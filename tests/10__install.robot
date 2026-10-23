*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Variables ***
${CONFIG}         {"host":"${HOST}","lets_encrypt":false,"http2https":true,"admin_user":"admin","admin_password":"${ADMIN_PASS}","admin_email":"admin@example.org","site_name":"CI"}
${CUSTOM_LDAP}    {"host":"${HOST}","lets_encrypt":false,"http2https":true,"ldap_enabled":true,"ldap_source":"custom","ldap_url":"ldaps://ldap.ci.test:636","ldap_tls_verify":true,"ldap_schema":"ad","ldap_base_dn":"DC=ci,DC=test","ldap_bind_dn":"CN=svc,DC=ci,DC=test","ldap_bind_password":"Bind#Pass 34"}
# Ubuntu package with the PHP2Shell fix (CVE-2026-109618/109619)
${PHP_FIXED}      8.3.6-0ubuntu0.24.04.13

*** Test Cases ***
Install the module
    IF    '${SCENARIO}' == 'update'
        ${output}  ${rc} =    Execute Command    add-module ${UPDATE_FROM} 1    return_rc=True
    ELSE
        ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1    return_rc=True
    END
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

The first configuration needs a super user
    # without one the Snipe-IT web installer would be open to the network
    ${out} =    Run task    module/${module_id}/configure-module    {"host":"${HOST}","lets_encrypt":false,"http2https":true}    rc_expected=2
    Should Be Equal    ${out[0]['error']}    admin_user_required

Configure the module
    Run task    module/${module_id}/configure-module    ${CONFIG}    decode_json=${FALSE}

Snipe-IT is installed and the installer is closed
    Wait Until Keyword Succeeds    60 times    5 seconds    The login page answers
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Should Be True    ${cfg['installed']}
    ${out} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code} \%{redirect_url}' -H 'Host: ${HOST}' https://127.0.0.1/setup
    Should Be Equal As Strings    ${out.strip()}    302 https://${HOST}/

The super user can log in
    Super user login works

Update to the image under test
    Skip If    '${SCENARIO}' != 'update'    scenario is ${SCENARIO}
    Run on node    api-cli run update-module --data '{"force":true,"module_url":"${IMAGE_URL}","instances":["${module_id}"]}'
    Wait Until Keyword Succeeds    60 times    5 seconds    The login page answers
    Super user login works

PHP carries the PHP2Shell fix
    # Ubuntu backports the fix without changing PHP_VERSION (8.3.6): compare
    # the package version inside the container (dpkg exits 1 when older)
    Run on node    runagent -m ${module_id} podman exec snipeit-app sh -c 'dpkg --compare-versions "$(dpkg-query -W -f "\\\${Version}" php8.3-common)" ge ${PHP_FIXED}'
    ${n} =    Run on node    runagent -m ${module_id} podman exec snipeit-app sh -c 'zgrep -c CVE-2026-109618 /usr/share/doc/php8.3-common/changelog.Debian.gz || true'
    Should Be True    ${n.strip()} >= 1

The scheduler runs
    ${state} =    Run on node    runagent -m ${module_id} systemctl --user is-active snipeit-scheduler.timer
    Should Be Equal As Strings    ${state.strip()}    active
    Wait Until Keyword Succeeds    20 times    10 seconds    The scheduler has run

Secrets are stored in passwords.env only
    Secrets are kept out of the module environment    ${module_id}
    ${keys} =    Run on node    runagent -m ${module_id} bash -c 'cut -d= -f1 "$AGENT_STATE_DIR/passwords.env" | sort | tr "\\n" " "'
    Should Be Equal As Strings    ${keys.strip()}    APP_KEY DB_PASSWORD MARIADB_PASSWORD MARIADB_ROOT_PASSWORD
    ${mode} =    Run on node    runagent -m ${module_id} bash -c 'stat -c \%a "$AGENT_STATE_DIR/snipeit.env"'
    Should Be Equal As Strings    ${mode.strip()}    600

Groups of an unknown user domain are an empty list
    ${out} =    Run task    module/${module_id}/list-ldap-groups    {"domain":"no-such-domain.ci.test"}
    Should Be Equal As Integers    ${{ len($out['groups']) }}    0

A custom LDAP server keeps its bind password out of the environment
    Run task    module/${module_id}/configure-module    ${CUSTOM_LDAP}    decode_json=${FALSE}
    ${cfg} =    Run task    module/${module_id}/get-configuration    {}
    Should Be True    ${cfg['ldap_enabled']}
    Should Be Equal    ${cfg['ldap_source']}    custom
    Should Be True    ${cfg['ldap_bind_password_set']}
    Should Be True    'ldap_bind_password' not in $cfg
    Secrets are kept out of the module environment    ${module_id}
    ${leaks} =    Run on node    runagent -m ${module_id} bash -c 'grep -c "Bind#Pass 34" "$AGENT_STATE_DIR/environment" || true'
    Should Be Equal As Integers    ${leaks.strip()}    0
    # the server does not exist: the local super user keeps working
    Wait Until Keyword Succeeds    30 times    5 seconds    The login page answers
    Super user login works

Back to the local login
    Run task    module/${module_id}/configure-module    {"host":"${HOST}","lets_encrypt":false,"http2https":true,"ldap_enabled":false}    decode_json=${FALSE}
    Wait Until Keyword Succeeds    30 times    5 seconds    The login page answers
    ${ldap} =    Run on node    runagent -m ${module_id} bash -c 'podman exec snipeit-mariadb sh -c "MYSQL_PWD=\\"\\$MARIADB_PASSWORD\\" mariadb -N -u snipeit snipeit -e \\"select ldap_enabled, ldap_pword is null from settings\\""'
    Should Be Equal As Strings    ${ldap.strip()}    0\t1

*** Keywords ***
The login page answers
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -H 'Host: ${HOST}' https://127.0.0.1/login
    Should Be Equal As Strings    ${code.strip()}    200

The scheduler has run
    # the last run of the oneshot unit ended, with exit status 0
    ${out} =    Run on node    runagent -m ${module_id} systemctl --user show snipeit-scheduler.service -p ExecMainExitTimestampMonotonic -p ExecMainStatus --value
    ${ts}    ${status} =    Evaluate    $out.split()
    Should Be True    ${ts} > 0
    Should Be Equal As Strings    ${status}    0
