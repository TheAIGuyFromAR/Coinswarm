import requests

API_KEY = "YOUR_CRYPTOCOMPARE_API_KEY"
BASE_URL = "https://min-api.cryptocompare.com"

pairs = [
    ("BTC", "USDC"),
    ("ETH", "USDC"),
    ("SOL", "USDC"),
    ("BTC", "ETH"),
    ("BTC", "SOL"),
    ("ETH", "SOL"),
    ("mSOL", "SOL"),
    ("BONK", "SOL"),
    ("JITO", "SOL"),
    # More Solana meme coins
    ("WIF", "SOL"),      # dogwifhat
    ("SAMO", "SOL"),     # Samoyedcoin
    ("POPCAT", "SOL"),
    ("HADES", "SOL"),
    ("CHAD", "SOL"),
    ("MEOW", "SOL"),
    ("PENG", "SOL"),
    ("BODEN", "SOL"),
    ("COPE", "SOL"),
    ("SHDW", "SOL"),     # Shadow Token
    ("CHEEMS", "SOL"),
    ("HINATA", "SOL"),
    ("CAT", "SOL"),
    ("SLOTH", "SOL"),
    ("SAI", "SOL"),
    ("TROLL", "SOL"),
    ("FISH", "SOL"),
    ("GIGA", "SOL"),
    ("SNEK", "SOL"),
    ("BNB", "USDC"),
    ("XRP", "USDC"),
    ("LINK", "USDC"),
    ("ARB", "USDC"),
    ("OP", "USDC"),
    ("ADA", "USDC"),
    ("DOGE", "USDC"),
    ("AVAX", "USDC"),
    ("TRX", "USDC"),
    # Solana meme coin flops and low-activity tokens
    ("GRAPE", "SOL"),
    ("HUSKY", "SOL"),
    ("KIN", "SOL"),
    ("ROPE", "SOL"),
    ("FIDA", "SOL"),
    ("STEP", "SOL"),
    ("SLIM", "SOL"),
    ("LIQ", "SOL"),
    ("MEDIA", "SOL"),
    ("SBR", "SOL"),
    ("SUNNY", "SOL"),
    ("TULIP", "SOL"),
    ("MER", "SOL"),
    ("POLIS", "SOL"),
    ("ATLAS", "SOL"),
    ("SYP", "SOL"),
    ("SAIKO", "SOL"),
    ("SCOPE", "SOL"),
    ("SNY", "SOL"),
]

def check_pair(fsym, tsym):
    url = f"{BASE_URL}/data/price"
    params = {"fsym": fsym, "tsyms": tsym, "api_key": API_KEY}
    resp = requests.get(url, params=params)
    return resp.status_code == 200 and tsym in resp.json()

for fsym, tsym in pairs:
    available = check_pair(fsym, tsym)
    print(f"{fsym}-{tsym}: {'Available' if available else 'Not available'}")