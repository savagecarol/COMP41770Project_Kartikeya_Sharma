# Blockchain Network Simulator

A real-time blockchain network simulator that demonstrates core concepts of distributed ledger technology including mining, transaction processing, and peer-to-peer networking. This system visualizes how transactions flow through a blockchain network with multiple miners, wallets, and a bootstrap node.

## 🌐 Live Demo

- **Backend API**: [https://comp41770project-kartikeya-sharma.onrender.com/](https://comp41770project-kartikeya-sharma.onrender.com/)
- **Frontend Logger**: [https://comp41770project-kartikeya-sharma-1.onrender.com/](https://comp41770project-kartikeya-sharma-1.onrender.com/)

> **Deployment**: Automatic deployment occurs on every push to the main branch via Render.

## 🔄 System Architecture Flow Diagram

```mermaid
graph TD
    A[Frontend Logger] <--WebSocket--> B[Flask Backend]
    B <--Socket Connection--> C[Bootstrap Node]
    C <--Registration--> D[Miner 1]
    C <--Registration--> E[Miner 2]
    C <--Registration--> F[Miner 3]
    C <--Registration--> G[Miner 4]
    D <--> E
    E <--> F
    F <--> G
    G <--> D
    H[Wallet 1] --> D
    I[Wallet 2] --> E
    J[Wallet N] --> F
    K[Test Script] --> B
    
    style A fill:#e1f5fe
    style B fill:#fce4ec
    style C fill:#fff3e0
    style D fill:#e8f5e9
    style E fill:#e8f5e9
    style F fill:#e8f5e9
    style G fill:#e8f5e9
    style H fill:#f3e5f5
    style I fill:#f3e5f5
    style J fill:#f3e5f5
    style K fill:#fafafa
```

The system consists of several interconnected components:
1. **Frontend Logger**: Real-time visualization of blockchain events
2. **Backend API**: Flask server handling WebSocket communications
3. **Bootstrap Node**: Registration point for all miners in the network
4. **Miners**: Process transactions, mine blocks, and maintain the blockchain
5. **Wallets**: Generate and send transactions between participants
6. **Test Script**: Orchestrates the entire simulation process

## 🧱 Core Components & Functionality

### Transaction Model ([models/transaction.py](file:///Users/apple/Documents/ucd/blockchain/models/transaction.py))
Represents a financial transaction in the blockchain network.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/transaction.py#L1-L5)**: Initializes a transaction with sender, receiver, fees, and amount
- **[tx_to_dict()](file:///Users/apple/Documents/ucd/blockchain/models/transaction.py#L39-L45)**: Serializes transaction to dictionary format
- **[from_dict()](file:///Users/apple/Documents/ucd/blockchain/models/transaction.py#L48-L54)**: Deserializes transaction from dictionary format
- Comparison operators: Enable priority queue sorting based on transaction fees

### Block Model ([models/block.py](file:///Users/apple/Documents/ucd/blockchain/models/block.py))
Represents a block in the blockchain containing multiple transactions.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L8-L13)**: Creates a block with transactions and previous block hash
- **[compute_hash()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L15-L24)**: Calculates SHA256 hash of the block contents
- **[build_merkle_root()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L26-L45)**: Constructs Merkle tree root from transactions
- **[mine_block()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L47-L53)**: Performs proof-of-work to find valid block hash
- **[to_dict()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L56-L65)** / **[from_dict()](file:///Users/apple/Documents/ucd/blockchain/models/block.py#L68-L76)**: Serialization/deserialization methods

### Wallet Model ([models/wallet.py](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py))
Represents a participant in the blockchain network who can send/receive transactions.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L6-L11)**: Initialize wallet with owner name and initial balance
- **[connect_to_bootstrap()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L13-L33)**: Establishes connection with bootstrap node to get miner list
- **[select_miner()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L35-L41)**: Randomly selects a miner for transaction processing
- **[connect_to_miner()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L43-L52)**: Establishes direct connection with a miner
- **[update_balance()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L54-L100)**: Queries miner for current wallet balance
- **[get_balance()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L102-L105)**: Returns current wallet balance
- **[send_transaction()](file:///Users/apple/Documents/ucd/blockchain/models/wallet.py#L107-L175)**: Sends transaction to another wallet through a miner

### Miner Model ([models/Miner.py](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py))
Processes transactions, mines blocks, and maintains blockchain state.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L12-L28)**: Initialize miner with network parameters
- **[start()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L30-L35)**: Starts miner services including server and connection maintenance
- **[auto_mine()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L37-L43)**: Automatically attempts to mine blocks when enough transactions exist
- **[connect_to_peers()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L46-L60)**: Establishes connections with other miners
- **[run_server()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L62-L73)**: Listens for incoming connections from wallets and miners
- **[handle_client()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L75-L105)**: Processes requests from connected clients
- **[register_to_bootstrap()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L107-L134)**: Registers with bootstrap node to join network
- **[maintain_miner_connections()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L136-L151)**: Keeps connections with other miners updated
- **[connect_to_miner()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L153-L166)**: Establishes connection with a specific miner
- **[get_miners_from_bootstrap()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L168-L173)**: Retrieves current list of miners from bootstrap node
- **[handle_wallet()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L175-L202)**: Handles communication with wallet clients
- **[handle_miner()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L204-L234)**: Handles communication with other miners
- **[add_transaction_to_mempool()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L236-L249)**: Adds new transaction to pending transactions pool
- **[broadcast_transaction()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L251-L257)**: Shares transaction with all connected miners
- **[produce_block()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L259-L274)**: Mines a new block from transactions in mempool
- **[add_block_to_chain()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L276-L292)**: Adds a newly mined block to the blockchain
- **[broadcast_block()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L294-L300)**: Shares newly mined block with all connected miners
- **[calculate_balance()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L302-L316)**: Computes wallet balance based on blockchain state
- **[stop()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L318-L335)**: Gracefully shuts down the miner

### Bootstrap Node ([models/bootstrapNode.py](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py))
Central registry for all miners in the network.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py#L11-L18)**: Initializes bootstrap node with host/port
- **[start()](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py#L20-L32)**: Starts listening for miner registrations
- **[handle_client()](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py#L34-L65)**: Processes registration and miner list requests
- **[receive_json_line()](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py#L67-L80)** / **[send_json_line()](file:///Users/apple/Documents/ucd/blockchain/models/bootstrapNode.py#L82-L87)**: JSON communication helpers

### Test Script ([test_script_v2.py](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py))
Orchestrates the entire blockchain simulation process.

- **[check_stop()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L22-L25)**: Checks if stop signal has been received and raises exception if so
- **[start_bootstrap()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L28-L34)**: Initializes and starts bootstrap node
- **[start_miners()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L37-L54)**: Creates and starts multiple miners
- **[setup_wallets()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L57-L69)**: Creates wallets and connects them to the network
- **[simulate_transactions()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L72-L97)**: Generates transactions between wallets
- **[print_mempools()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L100-L106)**: Displays current transaction pools of all miners
- **[print_blockchains()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L109-L114)**: Shows current state of all miner blockchains
- **[mine_block()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L117-L136)**: Triggers manual block mining process
- **[update_wallet_balances()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L139-L149)**: Updates and displays final wallet balances
- **[shutdown()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L152-L167)**: Gracefully stops all components
- **[test_blockchain()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L170-L210)**: Main orchestrator function that runs the full simulation
- **[stop_test()](file:///Users/apple/Documents/ucd/blockchain/test_script_v2.py#L214-L217)**: Stops ongoing test execution

## 🖥️ Frontend Logger (`blockchain-logger/`)

### BlockchainLogger Component ([BlockChainLogger.jsx](file:///Users/apple/Documents/ucd/blockchain/blockchain-logger/src/BlockChainLogger.jsx))
Real-time visualization dashboard for blockchain events.

- **State Management**: Manages logs, connection status, and test execution state
- **WebSocket Integration**: Connects to backend via Socket.IO for real-time updates
- **Log Filtering**: Separates logs by component type (bootstrap, miners, wallets, etc.)
- **Interactive UI**: Allows viewing individual log entries and full log sections
- **Test Controls**: Provides buttons to start/stop tests and clear logs

#### Key Functions:
- `useEffect()` hooks: Handle WebSocket connection lifecycle
- `startTest()`: Initiates blockchain simulation
- `clearLogs()`: Clears displayed logs
- [LogSection](file:///Users/apple/Documents/ucd/blockchain/blockchain-logger/src/BlockChainLogger.jsx#L89-L153): Component for displaying categorized logs
- [SectionModal](file:///Users/apple/Documents/ucd/blockchain/blockchain-logger/src/BlockChainLogger.jsx#L57-L87): Modal for viewing complete log sections
- Auto-scroll functionality: Keeps logs visible as they arrive

### Log Categories Displayed:
1. **Bootstrap Node**: Registration and coordination messages
2. **Miners**: Mining activities, block creation, and peer communications
3. **Wallets**: Transaction initiation and balance queries
4. **Test Logs**: Progress indicators and orchestration messages
5. **Errors**: Any system errors or exceptions

## ⚙️ Backend API ([api/index.py](file:///Users/apple/Documents/ucd/blockchain/api/index.py))

Central Flask server handling WebSocket communications and test orchestration.

### WebSocketLogger Class
Intercepts standard output and broadcasts log messages to connected clients.

- **[__init__()](file:///Users/apple/Documents/ucd/blockchain/models/Miner.py#L12-L28)**: Initializes logger with reference to original stdout
- **[write()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L22-L32)**: Captures print statements and emits them via WebSocket
- **[flush()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L34-L35)**: Ensures immediate delivery of log messages
- **[close()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L37-L38)**: Restores normal stdout behavior

### API Endpoints:
- **[home()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L56-L57)**: Health check endpoint returning simple confirmation
- **[health()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L110-L111)**: Status endpoint indicating server is operational

### WebSocket Event Handlers:
- **[handle_connect()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L60-L62)**: Manages new client connections
- **[handle_disconnect()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L65-L66)**: Handles client disconnections
- **[handle_start_test()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L69-L90)**: Initiates blockchain simulation
- **[handle_stop_test()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L93-L107)**: Stops ongoing blockchain simulation
- **[start_logging()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L42-L47)**: Starts capturing print statements for broadcasting
- **[stop_logging()](file:///Users/apple/Documents/ucd/blockchain/api/index.py#L49-L53)**: Stops logging and restores stdout

## 🛠️ Constants ([utils/constants.py](file:///Users/apple/Documents/ucd/blockchain/utils/constants.py))

Configuration values used throughout the system:
- **[TRANS_PER_BLOCK](file:///Users/apple/Documents/ucd/blockchain/utils/constants.py#L0-L0)**: Number of transactions per block (4)
- **[QUEUED_CONNECTION](file:///Users/apple/Documents/ucd/blockchain/utils/constants.py#L1-L1)**: Maximum queued connections (20)
- **[MINER_PORT](file:///Users/apple/Documents/ucd/blockchain/utils/constants.py#L2-L2)**: List of ports for miner instances ([6001, 6002, 6003, 6004])
- **[MINING_DIFFICULTY](file:///Users/apple/Documents/ucd/blockchain/utils/constants.py#L3-L3)**: Proof-of-work difficulty level (2 leading zeros)

## 🚀 Development & Deployment Workflow

### Continuous Deployment Process
```mermaid
flowchart LR
    A[Git Push to Main] --> B[GitHub Webhook]
    B --> C[Render Deployment Trigger]
    C --> D[Backend Build Process]
    C --> E[Frontend Build Process]
    D --> F[Backend Deploy]
    E --> G[Frontend Deploy]
    F --> H[Live API]
    G --> I[Live Logger]
```

1. Developer pushes code changes to main branch
2. GitHub notifies Render via webhook
3. Render simultaneously builds backend and frontend applications
4. Applications are deployed to production servers
5. Services become accessible via provided URLs

## ▶️ Running the Project Locally

You can run this blockchain simulator in several ways for local testing and development:

### Method 1: Comprehensive Test Script (Recommended)
```bash
python test_script_v2.py
```
This is the most comprehensive testing method that:
- Starts all components (bootstrap node, miners, wallets)
- Runs a full simulation with 50 transactions
- Shows real-time logs and status updates
- Best for testing the complete system functionality

### Method 2: Simple Test Script
```bash
python test_script_v1.py
```
A simpler version of the test script with fewer transactions and components.

### Method 3: Main Node Runner
```bash
python main.py
```
Starts the core blockchain network components without running transactions.
Useful for checking if basic network connectivity works.

### Method 4: Flask Backend Server
```bash
python api/index.py
```
Starts the Flask backend server that:
- Handles WebSocket connections
- Provides API endpoints
- Serves as the communication bridge between frontend and blockchain network

### Method 5: Frontend Logger
To run the frontend logger locally:

1. First, modify the WebSocket URL in the frontend code:
   - Open [blockchain-logger/src/BlockChainLogger.jsx](file:///Users/apple/Documents/ucd/blockchain/blockchain-logger/src/BlockChainLogger.jsx)
   - Change the Socket.IO URL to `http://localhost:5400`

2. Then run the frontend:
```bash
cd blockchain-logger
npm start
```

This starts the React development server and opens the blockchain logger in your browser.

### Prerequisites
Before running any of the above methods, ensure you have:
1. Python 3.7+ installed
2. Required Python packages installed: `pip install -r requirements.txt`
3. Node.js and npm installed (for frontend)
4. Frontend dependencies installed: `cd blockchain-logger && npm install`

## 📊 System Features

### Real-time Monitoring
- Live log streaming from all blockchain components
- Interactive log inspection capabilities

### Blockchain Simulation
- Complete blockchain network with multiple miners
- Transaction generation and propagation
- Proof-of-work mining demonstration
- Wallet balance management

### Network Visualization
- Peer-to-peer miner connections
- Transaction flow tracking
- Block propagation monitoring

### Educational Value
- Demonstrates core blockchain concepts
- Shows distributed consensus mechanisms
- Illustrates network communication patterns
- Provides insight into mining process

This comprehensive system provides a hands-on demonstration of how blockchain networks operate, with real-time visibility into the various processes that occur behind the scenes.