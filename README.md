# WebSocket Connection Manager

A Python-based AWS Lambda application that manages new WebSocket connections by storing connection IDs along with tenant and user information in DynamoDB.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Deployment](#deployment)
- [Repository Structure](#repository-structure)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Overview

This repository contains an AWS Lambda function that:
1. Processes new WebSocket connection events.
2. Validates the request by checking for an authorizer context.
3. Extracts tenant information (and optionally, a user ID) from the incoming connection request.
4. Persists the connection details in a DynamoDB table for further management and routing.

---

## Features

- **DynamoDB Persistence**: Stores connection information along with tenant details.
- **Authorization Checks**: Ensures that only authorized connection requests are processed.
- **Modular Design**: Code is organized for production readiness with clear separation between application logic and tests.
- **Testing & Mocks**: Comprehensive unit tests using `pytest` and [moto](https://github.com/spulec/moto) to mock AWS services.

---

## Architecture

1. **WebSocket Connection Trigger**: The Lambda function is invoked when a new WebSocket connection is established.
2. **Validation and Data Extraction**: The function extracts the connection ID from the request and validates the provided tenant information.
3. **DynamoDB Storage**: The connection information is stored in a DynamoDB table for later use by other parts of the system.
4. **Response Generation**: Based on the processing outcome, an appropriate HTTP status code and message are returned to the client.

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/websocket-connection-manager.git
   cd websocket-connection-manager