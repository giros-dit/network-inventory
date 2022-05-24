# network-inventory

This repository contains a prototype implementation of a network inventory. The components of the prototype are developed as Docker containers and deployed using docker-compose.

# Requirements

- Docker (_tested with 20.10.12_)
- docker-compose (_tested with 1.29.1_)
- Arista cEOS 2.47.4M (_more details below_)
- [Postman](https://www.postman.com)

## Arista cEOS routers

Before starting the docker-compose scenario, the Arista cEOS image must be downloaded and imported in the system.

1. Download Arista cEOS 2.47.4M image from [arista.com](https://www.arista.com/en/support/software-download).

2. Import image in Docker:
    ```bash
    docker import cEOS64-lab-4.27.4M.tar.xz ceos-image:4.27.4M
    ```

# Network Topology

The scenario deploys the network inventory along with a network topology as depicted below:

![topology](docs/prototype-network.png)

Two Arista cEOS routers, `r1` and `r2`, are deployed and interconnected through a point-to-point link. Additionally, the `vm1` and `vm2` containers emulate servers connected to each Arista router. These servers will help at testing end-to-end connectivity in the scenario.

The Arista routers also include a management interface in a `default` virtual network. This network will also be used the components of the network inventory to communicate with the routers.

## Quick Start

Deploy the scenario with docker-compose (execute with daemon flag to send logs to background):

```bash
docker-compose up -d
```

The first time you run this command it will take a couple of minutes. The reason to this is that docker-compose will build images for the network inventory components that were developed, namely, [catalog-connector](catalog-connector) and [platform-registry](platform-registry).

Once Docker images are successfully built, the network inventory is deployed and the network topology is configured. At startup, the `catalog-connector` will connect to the [YANG Catalog API](https://yangcatalog.org) and load all metadata. This process takes 30 minutes approximately.

## Stop the scenario

You can destroy the scenario by running:

```bash
docker-compose stop
```

This command will just stop all Docker containers. The docker-compose scenario has been configured to persist the context information that was stored in the NGSI-LD Context Broker. Thus, you can continue where you left off by simply starting the scenario again.

```bash
docker-compose up -d
```

## Clean slate scenario

In case you want start with a clean slate scenario, remove the docker volume for the Contex Broker:

```bash
docker volume remove network-inventory_scorpio-postgres-storage
```

Now you are ready to start the scenario as if it was the first time:

```bash
docker-compose up -d
```

# Postman Collection

This repository includes a [Postman collection](Network-Inventory.postman_collection.json) to facilate the interactions with the Context Broker through the NGSI-LD API as described in the paper.

The collection is divided in two main folders:

- **Platform Registry**: Contains a request to register router `r1` through the Platform Registry REST API. This is a preliminary step in the case study as this registration request triggers in the Platform Registry the discovery of capabilities of this particular Arista router.

- **Catalog Connector**: Contains a set of queries to the NGSI-LD API of the Context Broker. These queries are to be executed in order as covered in the paper.
