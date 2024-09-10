

from core.client import WebClient
import random
from loguru import logger
from core.Scroll import *

async def scroll_claim(account_id, key):
    web3 = Scroll(
        account_id, key
    )
    await web3.claim_airdrop()