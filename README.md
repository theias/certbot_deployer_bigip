certbot_deployer_bigip
===========

[Certbot Deployer] plugin for deploying certificates to F5 BIG-IP devices

> BIG-IP is a collection of hardware platforms and software solutions providing services focused on security, reliability, and performance. - [What is BIG-IP?]

This tool runs as a [Certbot] "deploy hook", and uploads and installs Certbot certificates to BIG-IP and optionally associates them with a profile.

# Requires

* Python 3.9+
* A local user on the target BIG-IP device with `Terminal Access` set to `tmsh`  (see [Users and SSH and shells](#users-and-ssh-and-shells))
* SSH configured to connect as the local BIG-IP user (see [Users and SSH and shells](#users-and-ssh-and-shells))
* <details>
    <summary>Compatible BIG-IP software version</summary>

    These are the minimum supported versions of BIG-IP devices according to [K15462: Managing SSL certificates for BIG-IP systems using tmsh]. Check the article for the full list of supported versions.

    * BIG-IP AAM
        - `12.X.X`
    * BIG-IP AFM
        - `11.X.X`
    * BIG-IP Analytics
        - `11.X.X`
    * BIG-IP APM
        - `11.X.X`
    * BIG-IP ASM
        - `11.X.X`
    * BIG-IP LTM
        - `11.X.X`
    * BIG-IP Edge Gateway
        - `11.X.X`
    * BIG-IP WebAccelerator
        - `11.X.X`
    * BIG-IP WOM
        - `11.X.X`
    </details>

[K15462: Managing SSL certificates for BIG-IP systems using tmsh]: https://my.f5.com/manage/s/article/K15462

# Installation

You can install with [pipx]:

```sh
pipx certbot_deployer_bigip
```

You can install with [pip]:

```sh
python3 -m pip install certbot_deployer_bigip
```

Or install from source:

```sh
git clone <url>
pip install certbot_deployer_bigip
```

# Usage

## Examples

All examples assume the tool is being run as a Certbot deploy hook, and the environment variable `RENEWED_LINEAGE` points to the live certificate directory just updated by Certbot.

### Install certificate on the BIG-IP device named with its expiry timestamp as `host.domain.tld.YYY-MM-DDTHH:MM:SS` (the default)

```
certbot-deployer bigip --host bigip.domain.tld
```

### Install certificate on the BIG-IP device and then synchronize device changes to a device group

```
certbot-deployer bigip --host bigip.domain.tld --sync-group yoursyncgroup
```

### Install certificate on the BIG-IP device and then associate it with a client-ssl profile. If the profile does not exist, it will be created.

```
certbot-deployer bigip --host bigip.domain.tld --profile-name yourprofile --profile-type client-ssl
```

### Print out the deployment tasks that would be taken, but do not run them

```
certbot-deployer bigip --host bigip.domain.tld --dry-run
```

## Users and SSH and shells

This tool runs all of its tasks on the target devices via SSH.

It expects:

* the local user on the BIG-IP to have `Terminal Access` set to `tmsh` and with appropriate permissions
* a working SSH configuration to connect to the target devices

### BIG-IP user permissions

The local user on the target BIG-IP device must be granted at least the `Certificate Manager` role in order to deploy certificates.

In order to also create/update the associated profiles on the BIG-IP, the user will require the `Administrator` role.

### SSH

Configuration for the SSH connection can be done via the configuration of the user running the tool.

E.g.:

```
# /home/user/.ssh/config
Host bigip-device.domain.tld
    User certbot_deploy
    Identityfile /home/user/.ssh/id_rsa
    Port 2022
```

## Reference

```
usage: certbot-deployer bigip [-h] --host HOST [--dest-temp-dir DEST_DIR_PATH]
                              [--cert-name CERT_NAME]
                              [--profile-name PROFILE_NAME]
                              [--profile-type PROFILE_TYPE]
                              [--sync-group SYNC_GROUP] [--dry-run]

BIG-IP subcommand
        Certbot Deployer plugin for deploying certificates to F5 BIG-IP devices


options:
  -h, --help            show this help message and exit
  --host HOST, -H HOST  BIG-IP host to target with changes.
  --dest-temp-dir DEST_DIR_PATH, -t DEST_DIR_PATH
                        The temp path on the BIG-IP to use when uploading the
                        certificates for installation. This tool will try to
                        zero out the certificates at the end of the run once
                        they are ingested into the BIG-IP config, but you
                        should probably try to put them in a "safe" place.
                        Default: `/var/tmp`
  --cert-name CERT_NAME, -c CERT_NAME
                        The name to give the certificate objects on the BIG-
                        IP. If not given, this tool will use the Common Name
                        from the certificate with the ISO8601-formatted `Not
                        After` value appended, e.g. `host.domain.tld.YYY-MM-
                        DDTHH:MM:SS`
  --profile-name PROFILE_NAME, -p PROFILE_NAME
                        The name of the profile to modify/create to use the
                        deployed certificateIf given, the corresponding
                        `--profile-type` is also required. If neither are
                        given, this tool will not create/modify any profiles.
  --profile-type PROFILE_TYPE, -r PROFILE_TYPE
                        The type of profile to create if necessary e.g.
                        `client-ssl`. See BIG-IP docs for details on all
                        profile types. If given, the corresponding `--profile-
                        name` is also required. If neither are given, this
                        tool will not create/modify any profiles.
  --sync-group SYNC_GROUP, -s SYNC_GROUP
                        The sync-group to synchronize to after the
                        certificates are deployed. This tool will not try to
                        sync the BIG-IP node if this argument is not given
  --dry-run, -d         Report the workflow steps that would run without
                        actually running them
```

# Limitations

* "Rollbacks" are not yet implemented (and may not be) in the case of failure during deployment.
    - This should not be able to go more "wrong" than failing to synchronize after modifying a profile (if one is even configured), as no other operations should be touching any existing BIG-IP resources.

# Contributing

Merge requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

To run the test suite:

```bash
# Dependent targets create venv and install dependencies
make
```

Please make sure to update tests along with any changes.

# License

License :: OSI Approved :: MIT License


[Certbot Deployer]: https://github.com/theias/certbot_deployer
[Certbot]: https://certbot.eff.org/
[What is BIG-IP?]: https://community.f5.com/kb/technicalarticles/what-is-big-ip/279398
[pip]: https://pip.pypa.io/en/stable/
[pipx]: https://pipx.pypa.io/
