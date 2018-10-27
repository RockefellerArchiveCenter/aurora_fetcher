# Aquarius

A microservice to fetch data from Aurora, then transform and deliver it to ArchivesSpace.

[![Build Status](https://travis-ci.org/RockefellerArchiveCenter/aquarius.svg?branch=master)](https://travis-ci.org/RockefellerArchiveCenter/aquarius)

## Setup

Clone the repository

    $ git clone git@github.com:RockefellerArchiveCenter/aquarius.git

Install [Docker](https://store.docker.com/search?type=edition&offering=community) (trust me, it makes things a lot easier)

Run docker-compose from the root directory

    $ cd aquarius
    $ docker-compose up

Once the application starts successfully, you should be able to access the application in your browser at `http://localhost:8000`

When you're done, shut down docker-compose

    $ docker-compose down

Or, if you want to remove all data

    $ docker-compose down -v


## Usage

![TransferRoutine diagram](transformer.png)

For an example of the data Aquarius expects from Aurora, see `fixtures/data/accession.json`.


### Routes

| Method | URL | Parameters | Response  | Behavior  |
|--------|-----|---|---|---|
|POST|/transfers| |200|Accepts accession data from Aurora, transforms it and saves a new accession in ArchivesSpace|
|GET|/transfers|`last_modified` - unix timestamp |200|Returns a list of Aurora objects|
|GET|/transfers/{id}| |200|Returns data about an individual transfer|
|POST|/process| |200|Runs the TransferRoutine process|
|GET|/status||200|Return the status of the microservice


### Logging

Aquarius uses `structlog` to output structured JSON logs. Logging can be configured in `aquarius/settings.py`.


### ArchivesSpace configuration

In order to successfully save data to ArchivesSpace, you will have to make some changes to some of the default enumerations:

* Accession Acquisition Type: add `donation`
* Extent Extent Type: add `bytes` and `files`
* File Version Use Statement: add `master` and `service-edited`


## License

MIT License. See [LICENSE](LICENSE) for details.
