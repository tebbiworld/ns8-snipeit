<?php

/*
 * Copyright (C) 2026 tebbi
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Helper of the NS8 module, mounted read-only into the app container and run
 * as the web server user:
 *
 *   php /usr/local/lib/ns8/ns8-snipeit.php status
 *   php /usr/local/lib/ns8/ns8-snipeit.php passport
 *   php /usr/local/lib/ns8/ns8-snipeit.php install  < admin.json
 *   php /usr/local/lib/ns8/ns8-snipeit.php ldap     < ldap.json
 *
 * The input comes as JSON on stdin, so passwords never appear on a command
 * line. The output is one JSON object on stdout; errors go to stderr with a
 * non-zero exit code.
 *
 * install does what the Snipe-IT web installer does in its last step
 * (SetupController::postSaveFirstAdmin, Snipe-IT 8.8): the first super user
 * and the settings row. With both present Setting::setupCompleted() is true
 * and the installer (/setup) redirects to the login page.
 * passport prepares the REST API like the web installer does with
 * passport:install (SetupController::setupMigrate): the OAuth keys in the data
 * volume and the personal access client, which users need to create API keys.
 * Existing keys and clients are kept, so issued API tokens stay valid.
 * ldap stores the directory login like the LDAP settings page does
 * (SettingsController::postLdapSettings): the bind password encrypted with
 * the application key (Crypt::encrypt).
 */

declare(strict_types=1);

use App\Models\Setting;
use App\Models\User;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Crypt;
use Illuminate\Support\Facades\DB;
use Laravel\Passport\Passport;

const APP_ROOT = '/var/www/html';

require APP_ROOT.'/vendor/autoload.php';
$app = require APP_ROOT.'/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

/** Print the result and stop. */
function finish(array $result): never
{
    echo json_encode($result, JSON_UNESCAPED_SLASHES), "\n";
    exit(0);
}

/** Report an error without the input (it may hold passwords) and stop. */
function fail(string $message): never
{
    fwrite(STDERR, 'ns8-snipeit: '.$message."\n");
    exit(1);
}

/** The JSON object on stdin. */
function read_input(): array
{
    $data = json_decode((string) stream_get_contents(STDIN), true);
    if (! is_array($data)) {
        fail('the input is not a JSON object');
    }

    return $data;
}

function required_string(array $data, string $key): string
{
    $value = $data[$key] ?? '';
    if (! is_string($value) || trim($value) === '') {
        fail("missing value: $key");
    }

    return trim($value);
}

function status(): never
{
    finish([
        'setup_completed' => Setting::setupCompleted(),
        'version' => config('version.app_version'),
    ]);
}

function passport(): never
{
    $created = [];
    if (! file_exists(storage_path('oauth-private.key')) || ! file_exists(storage_path('oauth-public.key'))) {
        if (Artisan::call('passport:keys', ['--no-interaction' => true]) !== 0) {
            fail('passport:keys failed: '.trim(Artisan::output()));
        }
        $created[] = 'keys';
    }
    if (! Passport::personalAccessClient()->exists()) {
        $code = Artisan::call('passport:client', [
            '--personal' => true,
            '--name' => 'Snipe-IT Personal Access Client',
            '--no-interaction' => true,
        ]);
        if ($code !== 0) {
            fail('passport:client failed: '.trim(Artisan::output()));
        }
        $created[] = 'personal access client';
    }

    finish(['created' => $created]);
}

function install(array $data): never
{
    if (Setting::setupCompleted()) {
        finish(['created' => false, 'reason' => 'already installed']);
    }

    $username = required_string($data, 'username');
    $email = required_string($data, 'email');
    required_string($data, 'first_name');
    $password = $data['password'] ?? '';
    if (! is_string($password) || strlen($password) < 12) {
        fail('the password needs at least 12 characters');
    }

    // a failed step throws: DB::transaction rolls the user back, so a second
    // attempt does not find a half-finished installation
    try {
        DB::transaction(function () use ($data, $username, $email, $password) {
            create_admin($data, $username, $email, $password);
        });
    } catch (RuntimeException $e) {
        fail($e->getMessage());
    } catch (Illuminate\Database\QueryException $e) {
        // the message carries the SQL bindings (password hash): log the
        // error code only
        fail('database error '.$e->getCode().' while creating the administrator');
    }

    finish(['created' => true]);
}

function create_admin(array $data, string $username, string $email, string $password): void
{
    $user = new User;
    $user->first_name = required_string($data, 'first_name');
    $user->last_name = trim((string) ($data['last_name'] ?? '')) ?: 'Administrator';
    $user->username = $username;
    $user->email = $email;
    $user->activated = 1;
    $user->permissions = json_encode(['superuser' => 1]);
    $user->password = bcrypt($password);
    if (! $user->save()) {
        throw new RuntimeException('the administrator was not created: '.implode(' ', $user->getErrors()->all()));
    }

    $settings = Setting::first() ?? new Setting;
    $settings->site_name = trim((string) ($data['site_name'] ?? '')) ?: 'Snipe-IT';
    $settings->alert_email = $email;
    $settings->alerts_enabled = 1;
    $settings->pwd_secure_min = 12;
    $settings->brand = 1;
    $settings->locale = (string) ($data['locale'] ?? 'en-US');
    $settings->default_currency = (string) ($data['currency'] ?? 'EUR');
    $settings->link_light_color = '#296282';
    $settings->link_dark_color = '#296282';
    $settings->nav_link_color = '#FFFFFF';
    $settings->email_domain = substr(strrchr($email, '@') ?: '@', 1);
    $settings->email_format = 'filastname';
    $settings->next_auto_tag_base = 1;
    $settings->created_by = $user->id;
    if (! $settings->save()) {
        throw new RuntimeException('the settings were not saved: '.implode(' ', $settings->getErrors()->all()));
    }
}

function ldap(array $data): never
{
    $settings = Setting::getSettings();
    if ($settings === null) {
        fail('Snipe-IT is not installed yet');
    }

    if (empty($data['enabled'])) {
        // the stored bind password is dropped with the directory login
        $settings->ldap_enabled = 0;
        $settings->ldap_pword = null;
    } else {
        $settings->ldap_enabled = 1;
        $settings->ldap_server = required_string($data, 'server');
        $settings->ldap_tls = empty($data['start_tls']) ? 0 : 1;
        $settings->ldap_server_cert_ignore = empty($data['ignore_certificate']) ? 0 : 1;
        $settings->ldap_uname = required_string($data, 'bind_dn');
        $settings->ldap_pword = Crypt::encrypt(required_string($data, 'bind_password'));
        $settings->ldap_basedn = required_string($data, 'base_dn');
        $settings->ldap_filter = required_string($data, 'filter');
        $settings->ldap_username_field = required_string($data, 'username_field');
        $settings->ldap_auth_filter_query = required_string($data, 'auth_filter_query');
        $settings->ldap_fname_field = (string) ($data['first_name_field'] ?? 'givenname');
        $settings->ldap_lname_field = (string) ($data['last_name_field'] ?? 'sn');
        $settings->ldap_email = (string) ($data['email_field'] ?? 'mail');
        $settings->ldap_version = 3;
        $settings->is_ad = empty($data['is_ad']) ? 0 : 1;
        $settings->ad_domain = (string) ($data['ad_domain'] ?? '');
        // LDAP passwords are never copied into the Snipe-IT database: a
        // directory account can only log in while the directory accepts it
        $settings->ldap_pw_sync = 0;
    }
    if (! $settings->save()) {
        fail('the LDAP settings were not saved: '.implode(' ', $settings->getErrors()->all()));
    }

    finish(['ldap_enabled' => (bool) $settings->ldap_enabled]);
}

$command = $argv[1] ?? '';
match ($command) {
    'status' => status(),
    'passport' => passport(),
    'install' => install(read_input()),
    'ldap' => ldap(read_input()),
    default => fail("unknown command: $command"),
};
