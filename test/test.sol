/**
 *Submitted for verification at Etherscan.io on 2021-07-07
 */

// SPDX-License-Identifier: NONE

pragma solidity ^0.8.21;

contract Test {
    address c_owner;

    struct UserData {
        uint256 balance;
        uint256[4] ownership;
    }
    mapping(address => UserData) userData;

    address[1024] tokenOwners;
    address[1024] tokenApprovals;
    mapping(uint256 => string) tokenURIs;

    mapping(address => mapping(address => bool)) private operatorApprovals;

    bytes4 private constant _ERC721_RECEIVED = 0x150b7a02;
    bytes4 private constant _INTERFACE_ID_ERC165 = 0x01ffc9a7;
    bytes4 private constant _INTERFACE_ID_ERC721 = 0x80ac58cd;
    bytes4 private constant _INTERFACE_ID_ERC721_METADATA = 0x5b5e139f;
    bytes4 private constant _INTERFACE_ID_ERC721_ENUMERABLE = 0x780e9d63;

    event Transfer(
        address indexed _from,
        address indexed _to,
        uint256 indexed _tokenId
    );
    event Approval(
        address indexed _owner,
        address indexed _approved,
        uint256 indexed _tokenId
    );
    event ApprovalForAll(
        address indexed _owner,
        address indexed _operator,
        bool _approved
    );

    // constructor() {
    //     c_owner = msg.sender;
    // }

    /// @notice Count all NFTs assigned to an owner
    function balanceOf(address _owner) external view returns (uint256) {
        require(_owner != address(0), "Query for zero address");
        return userData[_owner].balance;
    }

    /// @notice Find the owner of an NFT
    function ownerOf(uint256 tokenId) public view returns (address) {
        if (tokenId < 1024) {
            address owner = tokenOwners[tokenId];
            if (owner != address(0)) return owner;
        }
        revert("Query for nonexistent tokenId");
    }

    function _transfer(address _from, address _to, uint256 _tokenId) internal {
        require(_from != address(0));
        require(_to != address(0));
        address owner = ownerOf(_tokenId);
        // require(_from == owner);
        if (
            msg.sender == c_owner ||
            msg.sender == owner ||
            getApproved(_tokenId) == msg.sender ||
            isApprovedForAll(owner, msg.sender)
        ) {
            delete tokenApprovals[_tokenId];
            removeOwnership(_from, _tokenId);
            addOwnership(_to, _tokenId);
            emit Transfer(_from, _to, _tokenId);
            return;
        }
        revert("Caller is not owner nor approved");
    }

    function removeOwnership(address _owner, uint256 _tokenId) internal {
        UserData storage data = userData[_owner];
        data.balance -= 1;
        uint256 idx = _tokenId / 256;
        uint256 bitfield = data.ownership[idx];
        data.ownership[idx] = bitfield & ~(uint256(1) << (_tokenId % 256));
    }

    function addOwnership(address _owner, uint256 _tokenId) internal {
        tokenOwners[_tokenId] = _owner;
        UserData storage data = userData[_owner];
        data.balance += 1;
        uint256 idx = _tokenId / 256;
        uint256 bitfield = data.ownership[idx];
        data.ownership[idx] = bitfield | (uint256(1) << (_tokenId % 256));
    }

    function transferFrom(
        address _from,
        address _to,
        uint256 _tokenId
    ) external {
        _transfer(_from, _to, _tokenId);
    }

    function approve(address approved, uint256 tokenId) public {
        address owner = ownerOf(tokenId);
        require(
            msg.sender == owner || isApprovedForAll(owner, msg.sender),
            "Not owner nor approved for all"
        );
        tokenApprovals[tokenId] = approved;
        emit Approval(owner, approved, tokenId);
    }

    function getApproved(uint256 tokenId) public view returns (address) {
        //ownerOf(tokenId);
        return tokenApprovals[tokenId];
    }

    /// @notice Query if an address is an authorized operator for another address
    function isApprovedForAll(
        address owner,
        address operator
    ) public view returns (bool) {
        return operatorApprovals[owner][operator];
    }

    function assertOwnership(uint256[] memory tokenIds) public {
        for (uint256 i = 0; i < 1; i++) {
            uint256 tokenId = tokenIds[i];
            c_owner = address(0);
            emit Transfer(address(0), ownerOf(tokenId), tokenId);
        }
        // emit Transfer(address(0), ownerOf(tokenIds[0]), tokenIds[0]);
    }
    function assertOwnership(uint256 tokenId) public {
        emit Transfer(address(0), ownerOf(tokenId), tokenId);
    }
}
