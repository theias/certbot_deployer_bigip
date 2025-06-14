# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 1.1.1 - 2025-06-04
### Fixed
- Fix regression which set `required=True` for `--host` and broke reading of that param from the certbot deployer config file

## 1.1.0 - 2025-05-16
### Changed
- Update certbot_deployer version
- Update tests to use new testing fixture

## 1.0.2 - 2025-04-16
### Changed
- Remove args-from-ENV as this tool is intended to be launched directly by certbot which cannot be configured to take advantage of this
- Remove `wheel` from `build-system.requires`

### Fixed
- Move from deprecated `cert` and `key` args for `tmsh [create|modify] profile` to new `cert-key-chain`

## 1.0.1 - 2025-04-11
### Fixed
- Update certbot_deployer version

## 1.0.0 - 2025-03-21
### Added
- Add `version` classvar to BigipDeployer to support `--version` in `certbot-deployer`

### Changed
- Shift the order of operations so that the key is deployed before the certificate

## 0.5.1 - 2025-03-20
### Fixed
- Bring all internal cli argument names into line with their user-facing names for ease of reference in configuration file

## 0.5.0 - 2025-03-20
### Fixed
- Alter arg parsing to allow "required" arguments to come from the Certbot Deployer config file

## 0.4.0 - 2025-03-20
### Fixed
- Removed external requirement for the `scp` command, now doing SCP purely via Python

## 0.3.1 - 2025-03-07
### Fixed
- Fix broken command in `save` workflow step

## 0.3.0 - 2025-03-07
### Changed
- Switch dry run intro message from stderr to stdout

### Added
- Add a new workflow step to save running config before optional sync

## 0.2.2 - 2025-03-02
### Fixed
- Fix bad `description` in setup

## 0.2.1 - 2025-03-01
### Changed
- developing workflows

## 0.2.0 - 2025-02-28
### Added
- Add examples to help output
- Add a `--dry-run` option to just print the tasks it would have done

## 0.1.0 - 2025-02-26
### Changed
- prep for release

## 0.0.1 - 2025-02-25
### Added
- initial commit
