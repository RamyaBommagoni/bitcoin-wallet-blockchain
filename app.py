from flask import Flask, render_template, request, redirect, url_for, flash, session
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import hashlib, json, datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ===== Wallet Setup =====
class Wallet:
    def __init__(self, name, username, password):
        self.name = name
        self.username = username
        self.password = password
        self.account = hashlib.sha256(username.encode()).hexdigest()[:10]
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        self.balance = 10

wallets = {
    name.lower(): Wallet(name, name.lower(), name.lower() + "123")
    for name in ["Ramya", "Siva", "Pavani", "Guru", "Saranya"]
}

# ===== Blockchain Classes =====
class Block:
    def __init__(self, index, timestamp, transactions, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_data = json.dumps({
            'index': self.index,
            'timestamp': str(self.timestamp),
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_data.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        genesis_block = Block(0, str(datetime.datetime.now()), [], "0")
        self.chain = [genesis_block]

    def add_block(self, block):
        self.chain.append(block)

blockchain = Blockchain()
transactions_pool = []

# ===== Helpers =====
def sign_transaction(sender_wallet, recipient_name, amount):
    message = f"{sender_wallet.name} sends {amount} to {recipient_name}"
    signature = sender_wallet.private_key.sign(message.encode()).hex()
    return {
        'sender': sender_wallet.name,
        'recipient': recipient_name,
        'amount': amount,
        'signature': signature
    }

def verify_transaction(txn):
    sender = txn['sender'].lower()
    message = f"{txn['sender']} sends {txn['amount']} to {txn['recipient']}".encode()
    signature = bytes.fromhex(txn['signature'])
    try:
        return wallets[sender].public_key.verify(signature, message)
    except:
        return False

# ===== Routes =====
@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username'].lower()
        pwd = request.form['password']
        if uname in wallets and wallets[uname].password == pwd:
            session['username'] = uname
            return redirect(url_for('dashboard'))
        flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out.")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = wallets[session['username']]
    return render_template('index.html', user=user, wallets=wallets, transactions=transactions_pool, blockchain=blockchain.chain)

@app.route('/send', methods=['POST'])
def send():
    if 'username' not in session:
        return redirect(url_for('login'))
    sender_name = session['username']
    recipient_name = request.form['recipient']
    amount = int(request.form['amount'])

    sender_wallet = wallets[sender_name]
    recipient_wallet = wallets[recipient_name.lower()]

    if sender_wallet.balance < amount:
        flash("Insufficient balance.")
        return redirect(url_for('dashboard'))

    txn = sign_transaction(sender_wallet, recipient_wallet.name, amount)

    if verify_transaction(txn):
        transactions_pool.append(txn)
        sender_wallet.balance -= amount
        recipient_wallet.balance += amount
        flash("✅ Transaction successfully added to the pool.")
    else:
        flash("Transaction failed signature verification.")
    return redirect(url_for('dashboard'))

@app.route('/mine', methods=['POST'])
def mine():
    if 'username' not in session:
        return redirect(url_for('login'))

    miner = wallets[session['username']]
    timestamp = request.form['timestamp']
    block_data = request.form['data']
    previous_hash = request.form['prev_hash']

    try:
        txns = json.loads(block_data)
    except:
        flash("❌ Invalid block data.")
        return redirect(url_for('dashboard'))

    block = Block(
        index=len(blockchain.chain),
        timestamp=timestamp,
        transactions=txns,
        previous_hash=previous_hash
    )

    blockchain.add_block(block)
    miner.balance += 2
    transactions_pool.clear()
    flash(f"🎉 Block #{block.index} mined successfully! You earned 2 BTC 💰")
    return redirect(url_for('dashboard'))

# Add this utility if needed for template
@app.context_processor
def inject_now():
    return {'now': lambda: datetime.datetime.now().isoformat()}

if __name__ == '__main__':
    app.run(debug=True)
