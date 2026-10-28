*** Settings ***
Library     SSHLibrary
Resource    api.resource

*** Test Cases ***
Add an asset to the database
    # an asset created through the API must come back with the restore
    ${token} =    Run on node    runagent -m ${module_id} podman exec -u docker snipeit-app php /var/www/html/artisan snipeit:make-api-key --user_id=1 --name=ci --key-only
    Set Suite Variable    ${TOKEN}    ${token.strip()}
    ${cat} =    API post    categories    {"name":"CI laptops","category_type":"asset"}
    ${model} =    API post    models    {"name":"CI model","category_id":${cat}}
    API post    hardware    {"asset_tag":"CI-0001","model_id":${model},"status_id":1}

Back up the module
    ${repo}    ${path} =    Back up the module to the cluster repository    ${module_id}
    Set Global Variable    ${BACKUP_REPO}    ${repo}
    Set Global Variable    ${BACKUP_PATH}    ${path}

Remove the original instance
    # The restored instance takes the same host name. After the removal wait
    # out logind's user stop delay: on Rocky 9 a module re-created within
    # seconds can get the same UID back and its agent never starts.
    Run on node    remove-module --no-preserve ${module_id}
    Sleep    45s

Restore into a new instance
    ${rid} =    Restore the module from the cluster repository    ${BACKUP_REPO}    ${BACKUP_PATH}
    Set Global Variable    ${restored_id}    ${rid}
    Set Global Variable    ${module_id}    ${rid}

The restored instance has settings, secrets and data
    ${cfg} =    Run task    module/${restored_id}/get-configuration    {}
    Should Be Equal    ${cfg['host']}    ${HOST}
    Should Be True    ${cfg['installed']}
    Secrets are kept out of the module environment    ${restored_id}
    Wait Until Keyword Succeeds    60 times    5 seconds    Super user login works
    # the API token was issued before the backup: application key and OAuth
    # keys came back with it
    ${tags} =    Run on node    curl -sSk -H 'Host: ${HOST}' -H 'Authorization: Bearer ${TOKEN}' -H 'Accept: application/json' https://127.0.0.1/api/v1/hardware | python3 -c 'import json,sys; print(" ".join(r["asset_tag"] for r in json.load(sys.stdin)["rows"]))'
    Should Be Equal As Strings    ${tags.strip()}    CI-0001

Without a super user no route is published
    # N1: an emptied database is noticed at the next start (restart,
    # update-module): the route is removed, the installer stays denied
    Run on node    runagent -m ${restored_id} bash -c 'podman exec snipeit-mariadb sh -c "MYSQL_PWD=\\"\\$MARIADB_PASSWORD\\" mariadb -u snipeit snipeit -e \\"SET FOREIGN_KEY_CHECKS=0; DELETE FROM users; DELETE FROM settings\\""'
    Run on node    runagent -m ${restored_id} systemctl --user restart snipeit-app.service
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -H 'Host: ${HOST}' https://127.0.0.1/setup
    Should Not Be Equal As Strings    ${code.strip()}    200
    Should Be Equal As Strings    ${code.strip()}    404
    ${cfg} =    Run task    module/${restored_id}/get-configuration    {}
    Should Not Be True    ${cfg['installed']}
    # without a new super user configure-module refuses to publish it
    Run task    module/${restored_id}/configure-module    {"host":"${HOST}","lets_encrypt":false,"http2https":true}    rc_expected=1    decode_json=${FALSE}
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -H 'Host: ${HOST}' https://127.0.0.1/setup
    Should Be Equal As Strings    ${code.strip()}    404

A backup of the emptied database fails
    # an empty dump would rotate the good snapshots out of the retention
    ${out}    ${err}    ${rc} =    Execute Command    runagent -m ${restored_id} bash -c 'cd "$AGENT_STATE_DIR" && module-dump-state'    return_stderr=True    return_rc=True    timeout=5 min
    Should Not Be Equal As Integers    ${rc}    0
    # refused for the emptied database, not for some other failure
    Should Contain    ${err}    no users or no settings

A new super user publishes it again
    Run task    module/${restored_id}/configure-module    {"host":"${HOST}","lets_encrypt":false,"http2https":true,"admin_user":"admin","admin_password":"${ADMIN_PASS}","admin_email":"admin@example.org"}    decode_json=${FALSE}
    ${cfg} =    Run task    module/${restored_id}/get-configuration    {}
    Should Be True    ${cfg['installed']}
    Wait Until Keyword Succeeds    30 times    5 seconds    Super user login works
    ${code} =    Run on node    curl -sSk -o /dev/null -w '\%{http_code}' -H 'Host: ${HOST}' https://127.0.0.1/setup
    Should Be Equal As Strings    ${code.strip()}    403

*** Keywords ***
API post
    [Documentation]    POST to the Snipe-IT REST API, return the id of the new object.
    [Arguments]    ${endpoint}    ${body}
    ${id} =    Run on node    curl -sSk -H 'Host: ${HOST}' -H 'Authorization: Bearer ${TOKEN}' -H 'Accept: application/json' -H 'Content-Type: application/json' -X POST https://127.0.0.1/api/v1/${endpoint} -d '${body}' | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["status"] == "success", d; print(d["payload"]["id"])'
    RETURN    ${id.strip()}
