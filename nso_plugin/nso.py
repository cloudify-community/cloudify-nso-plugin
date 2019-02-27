import requests
import sys

from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

STANDARD_HEADERS = {
    'Content-Type': 'application/vnd.yang.data+json'
}


def create(ctx):
    _ensure_preexisting(ctx)


def start(ctx):
    _ensure_preexisting(ctx)


def stop(ctx):
    _ensure_preexisting(ctx)


def delete(ctx):
    _ensure_preexisting(ctx)


def _ensure_preexisting(ctx):
    if not ctx.node.properties.get('use_existing', False):
        raise NonRecoverableError(
            'Can currently only handle pre-existing NSO')


def sync_from(ctx):
    _sync_from(ctx, ctx.node)


def add_device(ctx, device_ip):
    nso_url = _get_nso_base_url(ctx.target.node)
    nso_auth = _get_nso_auth(ctx.target.node)
    device_type = ctx.source.node.properties['device_type']
    device_name = ctx.source.node.properties['device_name']
    ned_id = ctx.source.node.properties['ned_id']

    # Add the device
    if ctx.operation.retry_number == 0:
        add_payload = {
            "tailf-ncs:device": {
                "name": device_name,
                "address": device_ip,
                "port": ctx.source.node.properties['port'],
                "authgroup": ctx.source.node.properties['auth_group'],
                "device-type": {
                    device_type: {
                        "ned-id": ned_id,
                        "protocol": "ssh"
                    }
                },
                "state": {
                    "admin-state": "unlocked"
                }
            }
        }

        ctx.logger.info('Adding device...')
        response = requests.patch(
            '{0}/api/running/devices/device'.format(nso_url),
            json=add_payload,
            headers=STANDARD_HEADERS,
            auth=nso_auth)
        _test_response(ctx, response, 'device add')
    else:
        ctx.logger.info('Retried operation; skipping adding device')

    # Fetch host keys.

    ctx.logger.info('Fetching host keys...')
    response = requests.post(
        '{0}/api/operations/devices/device/{1}/ssh/fetch-host-keys'.format(
            nso_url, device_name),
        auth=nso_auth)

    try:
        response.raise_for_status()
        if '<result>failed</result>' in response.text:
            return ctx.operation.retry(
                message="Received failure status: {0}".format(response.text))
    except HTTPError as ex:
        return ctx.operation.retry(
            message="Received HTTP error: {0}".format(str(ex)))

    # Perform sync.
    _sync_from(ctx, ctx.target.node)


def remove_device(ctx):
    device_name = ctx.source.node.properties['device_name']
    nso_url = _get_nso_device_url(ctx.target.node, "running", device_name)
    response = requests.delete(nso_url,
                               headers=STANDARD_HEADERS,
                               auth=_get_nso_auth(ctx.target.node))
    _test_response(ctx, response, 'device remove')


def _get_nso_device_url(node, datastore, device_name):
    return _get_nso_url(
        node, datastore, "/devices/device/{0}".format(device_name))


def _get_nso_url(node, datastore, path):
    return "{0}/api/{1}/{2}".format(_get_nso_base_url(node), datastore, path)


def _get_nso_base_url(node):
    return 'http://{0}:{1}'.format(node.properties['ip'],
                                   node.properties['rest_port'])


def _sync_from(ctx, nso_node):
    nso_url = _get_nso_base_url(nso_node)

    ctx.logger.info("Executing sync-from...")

    response = requests.post(
        '{0}/api/running/devices/_operations/sync-from'.format(nso_url),
        headers=STANDARD_HEADERS,
        auth=_get_nso_auth(nso_node)
    )
    _test_response(ctx, response, 'sync-from')


def _get_nso_auth(node):
    return HTTPBasicAuth(username=node.properties['username'],
                         password=node.properties['password'])


def _test_response(ctx, response, desc):
    try:
        response.raise_for_status()
    except HTTPError as ex:
        _, _, tb = sys.exc_info()
        raise NonRecoverableError(
            'Failed during {0}'.format(desc),
            causes=[exception_to_error_cause(ex, tb)])
    else:
        ctx.logger.info('{0} response: {1}'.format(desc, response.text))
