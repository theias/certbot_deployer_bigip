# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
