import json
import os

import pytest


def test_cc_snapshot_exists(server, shell):
    result = shell.run(['which', 'cc-snapshot'], encoding='utf-8')
    assert result.return_code == 0


def test_cc_snapshot_sudowarn(server, shell):
    result = shell.run(['cc-snapshot'],
        encoding='utf-8',
        allow_error=True,
    )
    assert result.return_code == 1
    assert 'root' in result.output or 'sudo' in result.output


# test is stalling, probably waiting for input. snapshot should be
# reading the envvars?
# @pytest.mark.timeout(30)
# def test_cc_snapshot_auth_fast_fail(server, shell):
#     result = shell.run(['sudo', 'cc-snapshot'],
#         encoding='utf-8',
#         allow_error=True,
#         update_env={
#             'OS_USERNAME': 'not-a-real-user',
#             'OS_PASSWORD': 'not-a-password-if-it-is-thats-crazy',
#         },
#     )
#     assert result.return_code == 1
#     assert 'check username' in result.output


def test_cc_checks(server, shell):
    result = shell.run(['sudo', 'cc-checks'])
    assert result.return_code == 0
 
def test_cc_cloudfuse(server, shell, image):
    credentials = 'username={},password={},projectid={},region={},authurl={}'.format(os.environ['OS_USERNAME'], 
                                                                                  os.environ['OS_PASSWORD'], 
                                                                                  os.environ['OS_PROJECT_ID'], 
                                                                                  os.environ['OS_REGION_NAME'], 
                                                                                  os.environ['OS_AUTH_URL'])
    # Test the correct installation of cloudfuse
    result = shell.run(['cc-cloudfuse', 'mount', '-o', credentials, '-V'], allow_error=True, encoding='utf-8')
    assert 'fusermount version' in result.output
    # Test mounting Object Store
    # Create mounting point
    mounting_dir_name = 'test_mounting_point'
    shell.run(['mkdir', mounting_dir_name])
    shell.run(['cc-cloudfuse', 'mount', mounting_dir_name, '-o', credentials])
    # Compare with swift command
    swift_list = shell.run(['swift', 'list', '--os-auth-url', os.environ['OS_AUTH_URL'].replace('v3', 'v2.0'),'--os-username', os.environ['OS_USERNAME'], '--os-password', os.environ['OS_PASSWORD'], '--os-tenant-id', os.environ['OS_PROJECT_ID'], '--os-region-name', os.environ['OS_REGION_NAME'], '-V', '2'], encoding='utf-8', allow_error=True)
    cloudfuse_list = shell.run(['ls', mounting_dir_name], encoding='utf-8')
    # Ubuntu trusty has issue on running swift command
    if image['os'] != 'ubuntu-trusty':
        assert sorted(swift_list.output.split('\n')) == sorted(cloudfuse_list.output.split('\n'))
    # Unmount and cleanup
    shell.run(['cc-cloudfuse', 'unmount', mounting_dir_name])
    shell.run(['rmdir', mounting_dir_name])


def test_provenance_data(server, shell, image):
    with shell.open('/opt/chameleon/provenance.json', 'r') as f:
        provenance_data = json.load(f)

    if provenance_data:
        pytest.skip('provenance data missing (image created manually?)')

    assert image['os'] == provenance_data['build-os']
    assert image['variant'] == provenance_data['build-variant']


@pytest.mark.require_os(['centos7', 'ubuntu-xenial']) # trusty cloud-init is too old
def test_uids(server, shell):
    result = shell.run(['id', '-u', 'cc'], encoding='utf-8')
    assert int(result.output.strip()) == 1000

    result = shell.run(['id', '-u', 'ccadmin'], encoding='utf-8')
    assert int(result.output.strip()) == 1010


@pytest.mark.require_os(['centos7', 'ubuntu-xenial']) # trusty doesn't have RAPL
@pytest.mark.skip_variant('arm64')
def test_etrace2(server, shell):
    result = shell.run(['etrace2', 'sleep', '1'], encoding='utf-8')
    assert 'ETRACE2' in result.output


@pytest.mark.require_variant('gpu')
def test_cuda_driver_running(server, shell):
    # result = shell.run(['which', 'nvidia-smi'], encoding='utf-8')
    result = shell.run(['nvidia-smi'], encoding='utf-8')
    assert result.return_code == 0


@pytest.mark.require_variant('fpga')
def test_fpga(server, shell):
    result = shell.run(['aocl', 'diagnose'], encoding='utf-8')
    assert result.return_code == 0
