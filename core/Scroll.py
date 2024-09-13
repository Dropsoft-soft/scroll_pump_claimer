import json
import time
from web3 import Web3
from core.abi.abi import SCROLL_MAIN_ABI
from core.client import WebClient
from loguru import logger
import asyncio, random
from random_user_agent.user_agent import UserAgent
from core.request import global_request
from core.retry import retry
from core.utils import WALLET_PROXIES, intToDecimal, sleep
from user_data.config import FEE_MULTIPLIER, USE_PROXY
user_agent_rotator = UserAgent(software_names=['chrome'], operating_systems=['windows', 'linux'])

class Scroll(WebClient):
    def __init__(self, id:int, key: str):
        super().__init__(id, key, 'scroll')
        self.headers = {
            'user-agent': user_agent_rotator.get_random_user_agent(),
            'Content-Type': 'application/json'
        }

    @retry
    async def is_elligable_address(self):
        proxy = None
        if USE_PROXY == True:
            proxy = WALLET_PROXIES[self.key]
        url = f'https://api.scrollpump.xyz/api/Airdrop/GetReward?address={self.address}'
        
        response = await global_request(method='get', url=url, headers=self.headers, proxy=proxy)
        return response
  
    @retry  
    async def mintFromJSON(self, amount, signature):
        mint_contract = self.web3.eth.contract(address=Web3.to_checksum_address('0xCe64dA1992Cc2409E0f0CdCAAd64f8dd2dBe0093'), abi=SCROLL_MAIN_ABI)
        contract_txn = await mint_contract.functions.claim(amount, signature, '0x0000000000000000000000000000000000000000').build_transaction({
            'nonce': await self.web3.eth.get_transaction_count(self.address),
            'from': self.address,
            'gas': 0,
            'gasPrice': int(await self.web3.eth.gas_price*FEE_MULTIPLIER),
            'chainId': self.chain_id,
            'value': 0,
        })
        gas = await self.web3.eth.estimate_gas(contract_txn)
        contract_txn['gas'] = int(gas*1.1)
        status, tx_link = await self.send_tx(contract_txn)
        if status == 1:
            logger.success(f"[{self.id}] {self.address} | claim pump token | {tx_link}")
            await asyncio.sleep(5)
        else:
            logger.error(f"[{self.id}] {self.address} | claim pump token | tx is failed | {tx_link}")
      
    @retry
    async def getSign(self):
        proxy = None
        if USE_PROXY == True:
            proxy = WALLET_PROXIES[self.key]
        url = f'https://api.scrollpump.xyz/api/Airdrop/GetSign?address={self.address}'
        response = await global_request(method='get', url=url, headers=self.headers, proxy=proxy)
        return response
        
    async def claim_airdrop(self):
        try:
            is_elligable_response = await self.is_elligable_address()
            print(is_elligable_response)
            if 'data' in is_elligable_response:
                base_reward = int(is_elligable_response['data']['baseReward'])
                bonus_reward = int(is_elligable_response['data']['bonusReward'])
                total = base_reward+bonus_reward
                logger.info(f'elligable to claim: {total}')
                if total > 0:
                    is_claimed = await self.is_claimed()
                    if is_claimed:
                        logger.info('Drop claimed')
                    else:
                        sign_data = await self.getSign()
                        if 'sign' in is_elligable_response['data']:
                            signature = is_elligable_response['data']['sign']
                            await self.mintFromJSON(total, signature)
                        else:
                            logger.info(f'No sign data {sign_data}')
                else:
                    logger.info('skip')
            else:
                logger.warning('not elliable for claim')
        except Exception as error:
            logger.error(error)

    async def is_claimed(self):
        mint_contract = self.web3.eth.contract(address=Web3.to_checksum_address('0xCe64dA1992Cc2409E0f0CdCAAd64f8dd2dBe0093'), abi=SCROLL_MAIN_ABI)
        claimed = await mint_contract.functions.claimed(self.address).call()
        return claimed
