"""
Pé de manga NFT 🥭 (by cusma)
Plante e regue um pé de manga, grite oxê e colhe sua deliciosa manga NFT!

Usage:
  pe_de_manga.py plantar <mnemonic>
  pe_de_manga.py regar <mnemonic> <pe-de-manga-id>
  pe_de_manga.py colher <mnemonic> <pe-de-manga-id> <palavra>
  pe_de_manga.py [--help]

Commands:
  plantar    Plante um novo pé de manga (custa 0.1 ALGO).
  regar      Regue o pé de manga para deixar a manga crescer (custa 0.1 ALGO).
  colher     Diga a palavra certa e tire a manga do pé.

Options:
  -h --help
"""

import sys
from base64 import b64decode
from typing import List, Optional, Union

from algosdk import account, encoding, kmd, logic, mnemonic
from algosdk.error import AlgodHTTPError
from algosdk.future import transaction
from algosdk.v2client import algod, indexer
from docopt import docopt

from pe_de_manga_smart_contract import (
    GLOBAL_STATE,
    LOCAL_STATE,
    METHOD_REGA,
    compile_stateful,
    pe_de_manga_approval,
    pe_de_manga_clear,
)

# CONFIG
FUND_ACCOUNT_MICROALGOS = 100_000


# CLIENTS
def _algod_client(
    algod_address: str = "http://localhost:4001",
    algod_token: str = "a" * 64
) -> algod.AlgodClient:
    """Instantiate and return Algod client object."""
    return algod.AlgodClient(algod_token, algod_address)


def _indexer_client(
    indexer_address: str = "http://localhost:8980",
    indexer_token: str = "a" * 64
) -> indexer.IndexerClient:
    """Instantiate and return Indexer client object."""
    return indexer.IndexerClient(indexer_token, indexer_address)


def _kmd_client(
    kmd_address="http://localhost:4002",
    kmd_token="a" * 64
) -> kmd.KMDClient:
    """Instantiate and return a KMD client object."""
    return kmd.KMDClient(kmd_token, kmd_address)


# ACCOUNTS
class Account:
    def __init__(
        self,
        address: str,
        private_key: Optional[str],
        lsig: Optional[transaction.LogicSig] = None,
    ):
        self.address = address
        self.private_key = private_key
        self.lsig = lsig

    def mnemonic(self) -> str:
        return mnemonic.from_private_key(self.private_key)

    def is_lsig(self) -> bool:
        return bool(not self.private_key and self.lsig)

    @classmethod
    def create(cls) -> "Account":
        private_key, address = account.generate_account()
        return cls(private_key=private_key, address=str(address))

    @property
    def decoded_address(self):
        return encoding.decode_address(self.address)


def get_kmd_accounts(
    kmd_wallet_name="unencrypted-default-wallet", kmd_wallet_password=""
) -> List[Account]:

    kmd_client = _kmd_client()
    wallets = kmd_client.list_wallets()

    wallet_id = None
    for wallet in wallets:
        if wallet["name"] == kmd_wallet_name:
            wallet_id = wallet["id"]
            break

    if wallet_id is None:
        raise Exception("Wallet not found: {}".format(kmd_wallet_name))

    wallet_handle = kmd_client.init_wallet_handle(
        wallet_id, kmd_wallet_password)

    try:
        addresses = kmd_client.list_keys(wallet_handle)

        private_keys = [
            kmd_client.export_key(wallet_handle, kmd_wallet_password, addr)
            for addr in addresses
        ]

        kmd_accounts = [
            Account(address=addresses[i], private_key=private_keys[i])
            for i in range(len(private_keys))
        ]
    finally:
        kmd_client.release_wallet_handle(wallet_handle)

    return kmd_accounts


def sign(signer: Account, txn: transaction.Transaction):
    """Sign a transaction with an Account."""
    if signer.is_lsig():
        return transaction.LogicSigTransaction(txn, signer.lsig)
    else:
        assert signer.private_key
        return txn.sign(signer.private_key)


def sign_send_wait(signer: Account, txn: transaction.Transaction, debug=False):
    """Sign a transaction, submit it, and wait for its confirmation."""
    signed_txn = sign(signer, txn)
    tx_id = signed_txn.transaction.get_txid()

    if debug:
        transaction.write_to_file(
            [signed_txn], "/tmp/txn.signed", overwrite=True)

    _algod_client().send_transactions([signed_txn])
    transaction.wait_for_confirmation(_algod_client(), tx_id)
    return _algod_client().pending_transaction_info(tx_id)


def fund(faucet: Account, receiver: Account, amount=FUND_ACCOUNT_MICROALGOS):
    params = _algod_client().suggested_params()
    txn = transaction.PaymentTxn(
        faucet.address,
        params,
        receiver.address,
        amount
    )
    return sign_send_wait(faucet, txn)


def create_and_fund(faucet: Account) -> Account:
    new_account = Account.create()
    fund(faucet, new_account)
    return new_account


# SMART CONTRACT
def assemble_bytecode(client: algod.AlgodClient, src: str) -> bytes:
    return b64decode(client.compile(src)["result"])


def create_app(
    creator: Account,
    approval_bytecode: bytes,
    clear_bytecode: bytes,
    local_schema: transaction.StateSchema,
    global_schema: transaction.StateSchema,
    **kwargs,
):
    params = _algod_client().suggested_params()

    txn = transaction.ApplicationCallTxn(
        sender=creator.address,
        sp=params,
        index=0,
        on_complete=transaction.OnComplete.NoOpOC,
        local_schema=local_schema,
        global_schema=global_schema,
        approval_program=approval_bytecode,
        clear_program=clear_bytecode,
        **kwargs,
    )

    txid = _algod_client().send_transaction(txn.sign(creator.private_key))
    result = transaction.wait_for_confirmation(_algod_client(), txid, 3)
    return result["application-index"]


def decode_state(state):
    return {
        b64decode(s["key"]).decode(): b64decode(s["value"]["bytes"])
        if s["value"]["type"] == 1
        else int(s["value"]["uint"])
        for s in state
    }


def get_application_state(app_id: int) -> dict[str, Union[bytes, int]]:
    global_state = decode_state(
        _algod_client().application_info(app_id)["params"]["global-state"]
    )
    return global_state


# TRANSACTIONS
def optin_to_asset(user: Account, asset_id: int):
    params = _algod_client().suggested_params()
    txn = transaction.AssetTransferTxn(
        sender=user.address,
        sp=params,
        receiver=user.address,
        amt=0,
        index=asset_id
    )
    return sign_send_wait(user, txn)


def rega(user: Account, app_id: int):
    params = _algod_client().suggested_params()
    params.flat_fee = True
    params.fee = 2 * params.min_fee

    rega_txn = transaction.ApplicationNoOpTxn(
        sender=user.address,
        sp=params,
        index=app_id,
        app_args=[METHOD_REGA.encode()]
    )

    sign_send_wait(user, rega_txn)


def colhe(user: Account, app_id: int, asa_id: int, palavra: str):
    params = _algod_client().suggested_params()
    params.flat_fee = True
    params.fee = 2 * params.min_fee

    colhe_txn = transaction.ApplicationNoOpTxn(
        sender=user.address,
        sp=params,
        index=app_id,
        app_args=[palavra.encode()],
        foreign_assets=[asa_id],
    )

    sign_send_wait(user, colhe_txn)


def main():
    if len(sys.argv) == 1:
        # Display help if no arguments, see:
        # https://github.com/docopt/docopt/issues/420#issuecomment-405018014
        sys.argv.append("--help")

    args = docopt(__doc__)

    # Checking mnemonic format
    try:
        assert len(args["<mnemonic>"].split()) == 25
    except AssertionError:
        quit(
            "\n⚠️\tA mnemonic phrase tem que ter 25 palavras, "
            'no formato: "palavra_1 palavra_2 ... palavra_25"\n'
        )

    pk = mnemonic.to_private_key(args["<mnemonic>"])

    jardineiro = Account(
        address=account.address_from_private_key(pk),
        private_key=pk
    )

    if args["plantar"]:
        pe_de_manga_approval_bytecode = assemble_bytecode(
            _algod_client(), compile_stateful(pe_de_manga_approval())
        )

        pe_de_manga_clear_bytecode = assemble_bytecode(
            _algod_client(), compile_stateful(pe_de_manga_clear())
        )

        print(f"\n🌱 Plantando um pé de manga (com 0.1 ALGO)...\n")
        pe_de_manga_app_id = create_app(
            creator=jardineiro,
            approval_bytecode=pe_de_manga_approval_bytecode,
            clear_bytecode=pe_de_manga_clear_bytecode,
            local_schema=LOCAL_STATE,
            global_schema=GLOBAL_STATE,
        )

        pe_de_manga = Account(
            address=logic.get_application_address(pe_de_manga_app_id),
            private_key=None,
            lsig=None,
        )
        print(f"🌿 A plantinha tá crescendo...\n")
        fund(jardineiro, pe_de_manga)
        return print(f"🌳 Oba! O pé de manga {pe_de_manga_app_id} já "
                     f"cresceu!\n")

    if args["regar"]:
        pe_de_manga_app_id = int(args["<pe-de-manga-id>"])

        manga_id = int(get_application_state(
            pe_de_manga_app_id)["naMangueira"])

        if not manga_id:
            pe_de_manga = Account(
                address=logic.get_application_address(pe_de_manga_app_id),
                private_key=None,
                lsig=None,
            )
            print(f"\n🚿 Regando o pé de manga {pe_de_manga_app_id} "
                  f"(com 0.1 ALGO)...\n")
            fund(jardineiro, pe_de_manga)
            print(f"☀️  Uma manga tá nascendo...\n")
            rega(jardineiro, pe_de_manga_app_id)
            manga_id = int(get_application_state(
                pe_de_manga_app_id)["naMangueira"])
            quit(f"🥭️ A manga {manga_id} amadureceu! 🤩\n")
        else:
            try:
                print(f"\n🚿 Regando o pé de manga {pe_de_manga_app_id}...\n")
                rega(jardineiro, pe_de_manga_app_id)
            except AlgodHTTPError:
                quit(f"🥭️ Já tem a manga {manga_id} em cima da mangueira! 😅\n")

    if args["colher"]:
        pe_de_manga_app_id = int(args["<pe-de-manga-id>"])
        palavra = args["<palavra>"]

        manga_id = int(get_application_state(
            pe_de_manga_app_id)["naMangueira"])

        if manga_id:
            print(f"\n🪜 Subindo para colher a manga {manga_id}...\n")
            try:
                optin_to_asset(jardineiro, manga_id)
            except AlgodHTTPError:
                quit(f'😟 Não conseguiu alcançar a manga! Precisa ter 0.1 ALGO'
                     f' a mais na sua conta!\n')

            print(f"🗣  {palavra}!!!\n")
            try:
                colhe(jardineiro, pe_de_manga_app_id, manga_id, palavra)
                quit(f"🥭️ A manga {manga_id} è deliciosa! 🤤\n")
            except AlgodHTTPError:
                quit(f'😟 "{palavra}" não è a palavra certa!\n')
        else:
            quit(
                f"\n🍃 Eita! Não tem mais manga na mangueira "
                f"{pe_de_manga_app_id}... 😅\n"
            )


if __name__ == "__main__":
    main()
