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


​	

## Prerequisites

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

## Install

1. Python dependencies installation.

```sh
pip3 install -r requirements.txt
```

## Usage

### Local

To test one solidity file, use `-cnames` to specify contract name.

```sh
python3 tool.py -s test/EvohFixedMint.sol -cnames EvohFixedMint -j -glt 200 -ll 100 -dl 500
```

To test a specifc function, use `-fselector` to specifiy the function selector (`-as` option is provided for automatical solc version switch).

```sh
python3 tool.py -s test/EvohFixedMint.sol -cnames EvohFixedMint -fselector 23b872dd -as
```

For solidity project. Remember to use remap to link the outside libraries (openzeppelin, etc).

```sh
python3 tool.py -s "path/to/.sol" -rmp "remapping/import_lib/path" -cnames "contract name"
# example
python3 tool.py -s test/8liens/contracts/8liens/8liensMinter.sol -rmp erc721a=test/8liens/erc721a @openzeppelin=test/8liens/@openzeppelin -cnames \$8liensMinter -ll 50 -glt 60
```

Other utils: contract/project source code crawler (with complete code structure) from EtherScan. See <a href='./crawler/crawl.py'>crawler.py</a>. The utils can help recover the original structure of the DApp contracts to be fed into WakeMint with remap configuration.

```sh
python3 crawl.py --dir ./0x --caddress 0x # 0x is the contract address
```

Usage in the WakeMint CLI.

```sh
python3 tool.py -caddress 0xa4631a191044096834ce65d1ee86b16b171d8080 -cnames CreatureToadz -fselector 40c10f19
```

