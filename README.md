certbot_deployer_bigip
===========

[Certbot Deployer] plugin for deploying certificates to F5 BIG-IP devices

# Requires

* Python 3.9+
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

```
usage: certbot-deployer-bigip bigip [-h] --host HOST
                                    [--dest-temp-dir DEST_DIR_PATH]
                                    [--cert-name CERT_NAME]
                                    [--profile-name PROFILE_NAME]
                                    [--profile-type PROFILE_TYPE]
                                    [--sync-group SYNC_GROUP]

BIG-IP subcommand

options:
  -h, --help            show this help message and exit
  --host HOST, -H HOST  BIG-IP host to target with changes.
  --dest-temp-dir DEST_DIR_PATH, -t DEST_DIR_PATH
                        The temp path on the BIG-IP to use when uploading the
                        certificates for installation. This tool will try to
                        zero out the certificates at the end of the run once
                        they are ingested into the BIG-IP config, but you
                        should probably try to put them in a "safe" place
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
                        `client-ssl`. If given, the corresponding `--profile`
                        is also required. If neither are given, this tool will
                        not create/modify any profiles.
  --sync-group SYNC_GROUP, -s SYNC_GROUP
                        The sync-group to synchronize to after the
                        certificates are deployed. This tool will not try to
                        sync the BIG-IP node if this argument is not given

Examples:

            # <example descr>

            certbot-deployer-bigip bigip <args>

        
```

# Limitations

\[[...]\]

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
[pip]: https://pip.pypa.io/en/stable/
