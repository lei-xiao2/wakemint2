<p>
  <img alt="Static Badge" src="https://img.shields.io/badge/python-3.8-blue">
  <img alt="Static Badge" src="https://img.shields.io/badge/ubuntu-20.04-yellow">
  <a href="doc url" target="_blank">
    <img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" />
  </a>
</p>




<div align="center">
  <h3 align="center">WakeMint</h3>
  <p align="center">
    1. Datasets for sleepminting defect in NFT-related contract .
    <br/>
    2. Tool WakeMint for detecting sleepminting.
    <br />
  </p>
</div>


## Project Structure

- `experiment`: the result of our conducted experiments.
- `test`: some contracts for tool testing.
- Other directories are the tool's source codes.

There are corresponding README files in the core folders such as `experiment` for detailed introduction.



## Tool

### Prerequisites

-   Python >= 3.8
-   evm >= 1.10.21.
    Download version 1.10.21 (tested) from [go-ethereum](https://geth.ethereum.org/downloads) and add executable bins in the `$PATH`.

    ```sh
    wget https://gethstore.blob.core.windows.net/builds/geth-alltools-linux-amd64-1.10.21-67109427.tar.gz
    tar -zxvf geth-alltools-linux-amd64-1.10.21-67109427.tar.gz
    cp geth-alltools-linux-amd64-1.10.21-67109427/evm /usr/local/bin/ #$PATH
    ```

-   solc.
    Recommend solc-select to manage Solidity compiler versions.

    ```sh
    pip3 install solc-select
    ```

### Install

1. Python dependencies installation.

```sh
pip3 install -r requirements.txt
```

### Usage

#### Local

To test one solidity file, use `-cnames` to specify contract name.

```sh
python3 tool.py -s test/EvohFixedMint.sol -cnames EvohFixedMint
```

To test a specifc function, use `-fselector` to specifiy the function selector (`-as` option is provided for automatical solc version switch).

```sh
python3 tool.py -s test/EvohFixedMint.sol -cnames EvohFixedMint -fselector 23b872dd -as
```
