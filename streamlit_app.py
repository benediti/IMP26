import io
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
import bcrypt
from streamlit_searchbox import st_searchbox
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from firebase_admin import credentials, firestore, storage
import firebase_admin

COD_CLIENTE_IMPAKTO = 208831
FIRESTORE_COLLECTION = "pedido_itens"
FIRESTORE_PRODUCTS_COLLECTION = "produtos"
FIRESTORE_SETORES_COLLECTION = "setores"
FIRESTORE_PDF_BUCKET = "material-basico"
FIRESTORE_AUDIT_COLLECTION = "audit_trail"
FIRESTORE_USERS_COLLECTION = "users"
APP_PASSWORD = os.getenv("APP_PASSWORD", "admin123")  # Default for testing
SESSION_DEFAULTS = {
    "excel_data": None,
    "excel_source": "",
    "excel_bytes": b"",
    "cart": [],
    "selected_setor": None,
    "firestore_client": None,
    "edit_client": None,
    "edit_indices": [],
    "authenticated": False,
    "current_user": None,
}
SHEET_CONFIG = {
    "Produtos": None,
    "Setor": None,
    "Aguardando Aprovação": [
        "CòdClienteImpakto",
        "CódProImpakto",
        "Item",
        "Qtde",
        "$ Unitário",
        "$ Total",
        "Unidade",
        "Setor",
        "SETOR2",
    ],
    "Pedido": [
        "CòdClienteImpakto",
        "CódProImpakto",
        "Item",
        "Qtde",
        "$ Unitário",
        "$ Total",
        "Unidade",
        "Setor",
        "SETOR2",
    ],
}


def init_session_state() -> None:
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)
    
    # Ensure admin user exists on first run
    ensure_admin_user()
    
    # Auto-load from Firestore on first run
    if st.session_state.excel_data is None and firestore_enabled():
        sync_firestore_to_session()


def check_authentication() -> bool:
    """Simple password authentication."""
    if st.session_state.authenticated:
        return True
    
    if not firestore_enabled():
        st.session_state.authenticated = True
        st.session_state.current_user = "Offline"
        return True
    
    return False


def render_login() -> bool:
    """Render login page with Firestore user validation."""
    st.set_page_config(page_title="Sistema de Gestão - Login", layout="centered")
    st.markdown("# 🔐 Login - Sistema de Gestão de Pedidos")
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    with col1:
        username = st.text_input("👤 Usuário")
    with col2:
        password = st.text_input("🔑 Senha", type="password")
    
    if st.button("Entrar", use_container_width=True):
        if validate_user_credentials(username, password):
            st.session_state.authenticated = True
            st.session_state.current_user = username if username else "Usuario"
            st.success(f"✅ Bem-vindo, {st.session_state.current_user}!")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos!")
    
    st.divider()


def log_audit(action: str, details: Dict) -> None:
    """Log audit trail to Firestore."""
    if not firestore_enabled():
        return
    
    try:
        db = get_firestore_client()
        audit_log = {
            "action": action,
            "user": st.session_state.get("current_user", "unknown"),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "details": details,
        }
        db.collection(FIRESTORE_AUDIT_COLLECTION).add(audit_log)
    except Exception as exc:
        st.warning(f"⚠️ Erro ao registrar auditoria: {exc}")


def compare_orders(original: Dict, modified: Dict) -> Dict:
    """Compare original and modified orders to get changes."""
    changes = {}
    for key in ["Qtde", "Item", "$ Unitário", "$ Total"]:
        orig_val = original.get(key)
        mod_val = modified.get(key)
        if orig_val != mod_val:
            changes[key] = {"de": orig_val, "para": mod_val}
    return changes


# ============================================================================
# USER MANAGEMENT FUNCTIONS
# ============================================================================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def get_users_list() -> List[Dict]:
    """Fetch all users from Firestore."""
    if not firestore_enabled():
        return []
    
    try:
        db = get_firestore_client()
        users = []
        for doc in db.collection(FIRESTORE_USERS_COLLECTION).stream():
            user_data = doc.to_dict()
            user_data["username"] = doc.id
            users.append(user_data)
        return users
    except Exception as e:
        st.warning(f"⚠️ Erro ao carregar usuários: {e}")
        return []


def validate_user_credentials(username: str, password: str) -> bool:
    """Validate user credentials against Firestore users collection."""
    if not firestore_enabled():
        # Offline mode: allow with default password
        return password == APP_PASSWORD
    
    if not username or not password:
        return False
    
    try:
        db = get_firestore_client()
        doc = db.collection(FIRESTORE_USERS_COLLECTION).document(username).get()
        
        if not doc.exists:
            return False
        
        user_data = doc.to_dict()
        password_hash = user_data.get("password_hash", "")
        
        return verify_password(password, password_hash)
    except Exception as e:
        st.warning(f"⚠️ Erro ao validar credenciais: {e}")
        return False


def create_user(username: str, password: str, role: str = "user") -> bool:
    """Create a new user in Firestore."""
    if not firestore_enabled():
        st.error("❌ Firestore não disponível para criar usuários.")
        return False
    
    if not username or not password:
        st.error("❌ Usuário e senha são obrigatórios.")
        return False
    
    try:
        db = get_firestore_client()
        
        # Check if user already exists
        doc = db.collection(FIRESTORE_USERS_COLLECTION).document(username).get()
        if doc.exists:
            st.error(f"❌ Usuário '{username}' já existe.")
            return False
        
        # Create user
        user_data = {
            "password_hash": hash_password(password),
            "role": role,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection(FIRESTORE_USERS_COLLECTION).document(username).set(user_data)
        st.success(f"✅ Usuário '{username}' criado com sucesso!")
        log_audit("create_user", {"username": username, "role": role})
        return True
    except Exception as e:
        st.error(f"❌ Erro ao criar usuário: {e}")
        return False


def delete_user(username: str) -> bool:
    """Delete a user from Firestore."""
    if not firestore_enabled():
        st.error("❌ Firestore não disponível.")
        return False
    
    try:
        db = get_firestore_client()
        db.collection(FIRESTORE_USERS_COLLECTION).document(username).delete()
        st.success(f"✅ Usuário '{username}' deletado com sucesso!")
        log_audit("delete_user", {"username": username})
        return True
    except Exception as e:
        st.error(f"❌ Erro ao deletar usuário: {e}")
        return False


def update_user_password(username: str, new_password: str) -> bool:
    """Update a user's password."""
    if not firestore_enabled():
        st.error("❌ Firestore não disponível.")
        return False
    
    if not new_password:
        st.error("❌ Nova senha é obrigatória.")
        return False
    
    try:
        db = get_firestore_client()
        db.collection(FIRESTORE_USERS_COLLECTION).document(username).update({
            "password_hash": hash_password(new_password),
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        st.success(f"✅ Senha do usuário '{username}' atualizada com sucesso!")
        log_audit("update_user_password", {"username": username})
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar senha: {e}")
        return False


def ensure_admin_user():
    """Ensure admin user exists in Firestore on first run."""
    if not firestore_enabled():
        return
    
    try:
        db = get_firestore_client()
        doc = db.collection(FIRESTORE_USERS_COLLECTION).document("admin").get()
        
        if not doc.exists:
            admin_data = {
                "password_hash": hash_password("admin123"),
                "role": "admin",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
            db.collection(FIRESTORE_USERS_COLLECTION).document("admin").set(admin_data)
    except Exception as e:
        st.warning(f"⚠️ Erro ao garantir usuário admin: {e}")


def ensure_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[columns].copy()


def load_excel_data(bytes_data: bytes) -> Dict[str, pd.DataFrame]:
    buffer = io.BytesIO(bytes_data)
    workbook = pd.ExcelFile(buffer)
    sheets: Dict[str, pd.DataFrame] = {}

    for sheet_name, columns in SHEET_CONFIG.items():
        if sheet_name in workbook.sheet_names:
            df = workbook.parse(sheet_name)
        else:
            df = pd.DataFrame(columns=columns or [])

        if columns:
            df = ensure_columns(df, columns)

        sheets[sheet_name] = df

    for sheet_name in ("Produtos", "Setor"):
        if sheet_name not in sheets:
            sheets[sheet_name] = pd.DataFrame()

    return sheets


def set_excel_data(bytes_data: bytes, source_label: str) -> None:
    try:
        excel_data = load_excel_data(bytes_data)
    except Exception as exc:  # pragma: no cover - streamlit feedback
        st.error(f"Falha ao carregar planilha: {exc}")
        return

    st.session_state.excel_data = excel_data
    st.session_state.excel_source = source_label
    st.session_state.excel_bytes = bytes_data
    st.session_state.cart = []
    st.session_state.selected_setor = None
    st.toast(f"Planilha carregada de {source_label}", icon="✅")

def get_firestore_client():
    if st.session_state.get("firestore_client"):
        return st.session_state.firestore_client

    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not service_json:
        return None

    try:
        cred_dict = json.loads(service_json)
    except json.JSONDecodeError:
        st.error("FIREBASE_SERVICE_ACCOUNT_JSON invalido.")
        return None

    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIRESTORE_PDF_BUCKET
        })

    client = firestore.client()
    st.session_state.firestore_client = client
    return client


def firestore_enabled() -> bool:
    return get_firestore_client() is not None


def fetch_firestore_rows(status: Optional[str] = None) -> pd.DataFrame:
    db = get_firestore_client()
    if not db:
        return pd.DataFrame()

    query = db.collection(FIRESTORE_COLLECTION)
    if status:
        query = query.where("status", "==", status)

    rows = []
    for doc in query.stream():
        data = doc.to_dict()
        data["__doc_id"] = doc.id
        rows.append(data)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = ensure_columns(df, SHEET_CONFIG["Aguardando Aprovação"])
    df["__doc_id"] = pd.Series([row["__doc_id"] for row in rows])
    return df


def sync_firestore_to_session() -> None:
    if not firestore_enabled():
        return

    aguardando = fetch_firestore_rows("aguardando")
    pedido = fetch_firestore_rows("pedido")

    if st.session_state.excel_data is None:
        st.session_state.excel_data = {}

    st.session_state.excel_data["Aguardando Aprovação"] = aguardando
    st.session_state.excel_data["Pedido"] = pedido
    sync_firestore_reference_data()


def upload_pdf_to_storage(pdf_buffer: io.BytesIO, client_name: str) -> Optional[str]:
    """Upload PDF to Firestore Storage and return the path."""
    try:
        # Get Firebase Admin SDK instance
        if not firebase_admin._apps:
            get_firestore_client()  # Initialize if needed
        
        bucket = storage.bucket(FIRESTORE_PDF_BUCKET)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = f"previews/{client_name.replace(' ', '_')}_PREVIA_{timestamp}.pdf"
        blob = bucket.blob(pdf_name)
        
        # Upload PDF
        blob.upload_from_string(
            pdf_buffer.getvalue(), 
            content_type="application/pdf"
        )
        st.success(f"✅ PDF salvo em Storage: {pdf_name}")
        return pdf_name
    except Exception as exc:
        st.error(f"Erro ao salvar PDF no Storage: {exc}")
        return None


def save_rows_to_firestore(linhas: pd.DataFrame, status: str, pdf_buffer: Optional[io.BytesIO] = None) -> None:
    db = get_firestore_client()
    if not db:
        return

    # Upload PDF if provided
    pdf_path = None
    client_name = None
    if pdf_buffer and st.session_state.selected_setor:
        client_name = st.session_state.selected_setor.get("descricao", "cliente")
        pdf_path = upload_pdf_to_storage(pdf_buffer, client_name)

    for _, row in linhas.iterrows():
        payload = {
            "CòdClienteImpakto": row["CòdClienteImpakto"],
            "CódProImpakto": row["CódProImpakto"],
            "Item": row["Item"],
            "Qtde": int(row["Qtde"]),
            "$ Unitário": float(row["$ Unitário"]),
            "$ Total": float(row["$ Total"]),
            "Unidade": row["Unidade"],
            "Setor": row["Setor"],
            "SETOR2": row["SETOR2"],
            "status": status,
            "client_name": client_name,
            "pdf_path": pdf_path,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection(FIRESTORE_COLLECTION).add(payload)


def fetch_collection_df(collection: str, columns: List[str]) -> pd.DataFrame:
    db = get_firestore_client()
    if not db:
        return pd.DataFrame(columns=columns)

    rows = []
    for doc in db.collection(collection).stream():
        data = doc.to_dict()
        data["__doc_id"] = doc.id
        rows.append(data)

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df = ensure_columns(df, columns)
    df["__doc_id"] = pd.Series([row["__doc_id"] for row in rows])
    return df


def fetch_products_df() -> pd.DataFrame:
    columns = ["productCode", "name", "price"]
    return fetch_collection_df(FIRESTORE_PRODUCTS_COLLECTION, columns)


def fetch_setores_df() -> pd.DataFrame:
    columns = ["CódUnidade", "items__description"]
    return fetch_collection_df(FIRESTORE_SETORES_COLLECTION, columns)


def upsert_collection_from_df(collection: str, df: pd.DataFrame, key_field: str) -> None:
    db = get_firestore_client()
    if not db:
        return

    for _, row in df.iterrows():
        doc_id = str(row.get(key_field, "")).strip()
        if not doc_id:
            continue
        payload = row.drop(labels=["__doc_id"], errors="ignore").to_dict()
        db.collection(collection).document(doc_id).set(payload)


def sync_firestore_reference_data() -> None:
    if not firestore_enabled():
        return

    if st.session_state.excel_data is None:
        st.session_state.excel_data = {}

    st.session_state.excel_data["Produtos"] = fetch_products_df()
    st.session_state.excel_data["Setor"] = fetch_setores_df()


def get_storage_path() -> Optional[str]:
    path = os.getenv("ORDERS_WORKBOOK_PATH")
    if path and path.strip():
        return path
    return None


def render_sidebar() -> None:
    storage_path = get_storage_path()

    with st.sidebar:
        st.header("Gerenciar dados")
        
        if firestore_enabled():
            st.success("✅ Dados do Firestore carregados automaticamente")
            st.divider()
            
            if st.button("🔄 Recarregar dados do Firestore", use_container_width=True):
                sync_firestore_to_session()
                st.toast("Dados recarregados do Firestore.", icon="✅")

            if st.session_state.excel_data is not None:
                produtos_df = st.session_state.excel_data.get("Produtos", pd.DataFrame())
                setores_df = st.session_state.excel_data.get("Setor", pd.DataFrame())
                
                st.divider()
                st.caption("📤 Para atualizar Produtos/Setor, carregue Excel e envie:")
                
                uploaded = st.file_uploader("Carregar planilha (.xlsx)", type=["xlsx", "xls"])
                if uploaded is not None:
                    set_excel_data(uploaded.getvalue(), f"upload ({uploaded.name})")
                    st.rerun()
                
                if st.button("📤 Enviar Produtos/Setor para Firestore", use_container_width=True):
                    if produtos_df.empty or setores_df.empty:
                        st.error("Carregue uma planilha com Produtos e Setor antes de enviar.")
                    else:
                        upsert_collection_from_df(
                            FIRESTORE_PRODUCTS_COLLECTION,
                            produtos_df,
                            "productCode",
                        )
                        upsert_collection_from_df(
                            FIRESTORE_SETORES_COLLECTION,
                            setores_df,
                            "CódUnidade",
                        )
                        sync_firestore_reference_data()
                        st.toast("Produtos e setores enviados ao Firestore.", icon="✅")
        else:
            st.warning("⚠️ Firestore não disponível. Carregue uma planilha:")
            uploaded = st.file_uploader("Carregar planilha (.xlsx)", type=["xlsx", "xls"])
            if uploaded is not None:
                set_excel_data(uploaded.getvalue(), f"upload ({uploaded.name})")

        if storage_path:
            st.divider()
            st.caption(f"Arquivo do servidor: {storage_path}")
            if st.button("Carregar do servidor", use_container_width=True):
                if os.path.exists(storage_path):
                    with open(storage_path, "rb") as handler:
                        set_excel_data(handler.read(), os.path.basename(storage_path))
                else:
                    st.error("Arquivo configurado não encontrado no servidor.")


def build_workbook_bytes(data: Dict[str, pd.DataFrame]) -> io.BytesIO:
    """Build workbook using 'Excel Form Base.xlsx' as template if available."""
    from openpyxl import load_workbook
    
    # Try to load template
    model_path = os.path.join(os.path.dirname(__file__), "Excel Form Base.xlsx")
    if os.path.exists(model_path):
        # Load template and update sheets
        wb = load_workbook(model_path)
        
        # Clear existing data (keep headers)
        for sheet_name in ["Produtos", "Setor", "Aguardando Aprovação", "Pedido"]:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                # Delete all rows except the first (header)
                while ws.max_row > 1:
                    ws.delete_rows(2)
        
        # Write new data
        for sheet_name in ["Produtos", "Setor", "Aguardando Aprovação", "Pedido"]:
            if sheet_name in wb.sheetnames:
                df = data.get(sheet_name, pd.DataFrame())
                df = df.drop(columns=["__doc_id"], errors="ignore")
                
                ws = wb[sheet_name]
                # Write data starting from row 2 (after header)
                for r_idx, row in enumerate(df.itertuples(index=False), start=2):
                    for c_idx, value in enumerate(row, start=1):
                        ws.cell(row=r_idx, column=c_idx, value=value)
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer
    else:
        # Fallback: create from scratch
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sheet_name in ["Produtos", "Setor", "Aguardando Aprovação", "Pedido"]:
                df = data.get(sheet_name, pd.DataFrame())
                df = df.drop(columns=["__doc_id"], errors="ignore")
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        buffer.seek(0)
        return buffer


def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "tmp").replace(".", ",").replace("tmp", ".")


def parse_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def render_setor_selector(setor_df: pd.DataFrame) -> None:
    if setor_df.empty:
        st.error("A aba 'Setor' está vazia na planilha.")
        return

    required_cols = {"CódUnidade", "items__description"}
    missing = required_cols.difference(setor_df.columns)
    if missing:
        st.error(
            "A aba 'Setor' precisa conter as colunas: "
            + ", ".join(sorted(required_cols))
        )
        return

    setores = setor_df.dropna(subset=["CódUnidade", "items__description"]).copy()
    setores["codigo"] = setores["CódUnidade"].apply(parse_int)
    setores["descricao"] = setores["items__description"].astype(str)
    setores["label"] = setores.apply(
        lambda row: f"{row['codigo']} - {row['descricao']}", axis=1
    )

    if setores.empty:
        st.warning("Nenhum setor disponível.")
        return

    current_label = st.session_state.selected_setor.get("label") if st.session_state.selected_setor else None
    index = 0
    if current_label:
        try:
            index = setores["label"].tolist().index(current_label)
        except ValueError:
            index = 0

    if current_label and "search_setor" not in st.session_state:
        st.session_state["search_setor"] = current_label

    def setor_search(term: str) -> List[str]:
        if not term:
            return setores["label"].tolist()[:50]
        term_lower = term.lower()
        subset = setores.copy()
        subset["desc_lower"] = subset["descricao"].astype(str).str.lower()
        subset["code_lower"] = subset["codigo"].astype(str).str.lower()
        mask = (
            subset["desc_lower"].str.contains(term_lower)
            | subset["code_lower"].str.contains(term_lower)
        )
        subset = subset.loc[mask].copy()
        if subset.empty:
            return []
        subset["rank"] = (
            subset["desc_lower"].str.startswith(term_lower).astype(int) * 2
            + subset["code_lower"].str.startswith(term_lower).astype(int)
        )
        subset = subset.sort_values(["rank", "descricao"], ascending=[False, True])
        return subset["label"].tolist()[:50]

    selected_label = st_searchbox(
        setor_search,
        key="search_setor",
        label="2. Selecione o setor/cliente (digite para buscar)",
    )
    if not selected_label:
        st.info("Digite para buscar e selecione um setor/cliente.")
        return

    selected_row = setores[setores["label"] == selected_label].iloc[0]
    st.session_state.selected_setor = {
        "codigo": selected_row["codigo"],
        "descricao": selected_row["descricao"],
        "label": selected_row["label"],
    }



def render_product_selector(produtos_df: pd.DataFrame) -> Optional[dict]:
    if produtos_df.empty:
        st.error("A aba 'Produtos' está vazia na planilha.")
        return None

    required_cols = {"productCode", "name", "price"}
    missing = required_cols.difference(produtos_df.columns)
    if missing:
        st.error(
            "A aba 'Produtos' precisa conter as colunas: "
            + ", ".join(sorted(required_cols))
        )
        return None

    produtos = produtos_df.copy()
    produtos["price"] = pd.to_numeric(produtos.get("price"), errors="coerce").fillna(0.0)

    produtos = produtos.sort_values("name")
    produtos["label"] = produtos.apply(
        lambda row: f"{row['productCode']} - {row['name']}", axis=1
    )

    def produto_search(term: str) -> List[str]:
        if not term:
            return produtos["label"].tolist()[:50]
        term_lower = term.lower()
        subset = produtos.copy()
        subset["name_lower"] = subset["name"].astype(str).str.lower()
        subset["code_lower"] = subset["productCode"].astype(str).str.lower()
        mask = (
            subset["name_lower"].str.contains(term_lower)
            | subset["code_lower"].str.contains(term_lower)
        )
        subset = subset.loc[mask].copy()
        if subset.empty:
            return []
        subset["rank"] = (
            subset["name_lower"].str.startswith(term_lower).astype(int) * 2
            + subset["code_lower"].str.startswith(term_lower).astype(int)
        )
        subset = subset.sort_values(["rank", "name"], ascending=[False, True])
        return subset["label"].tolist()[:50]

    selected_label = st_searchbox(
        produto_search,
        key="search_produto",
        label="Produto (digite para buscar)",
    )
    if not selected_label:
        st.info("Digite para buscar um produto.")
        return None

    selected_row = produtos[produtos["label"] == selected_label].iloc[0]
    return selected_row.to_dict()


def add_item_to_cart(product: dict, quantity: int) -> None:
    preco = parse_float(product.get("price"))
    codigo = str(product.get("productCode"))
    nome = str(product.get("name"))

    for item in st.session_state.cart:
        if item["codigo"] == codigo:
            item["quantidade"] += quantity
            item["total"] = item["quantidade"] * item["preco_unitario"]
            break
    else:
        st.session_state.cart.append(
            {
                "codigo": codigo,
                "nome": nome,
                "quantidade": quantity,
                "preco_unitario": preco,
                "total": preco * quantity,
            }
        )


def render_cart() -> None:
    cart = st.session_state.cart
    if not cart:
        st.info("Nenhum item no carrinho ainda.")
        return

    st.subheader("4. Itens do pedido")
    header_cols = st.columns([1.2, 3.5, 1, 1, 1, 0.8])
    header_cols[0].markdown("**Código**")
    header_cols[1].markdown("**Produto**")
    header_cols[2].markdown("**Qtd**")
    header_cols[3].markdown("**$ Unit.**")
    header_cols[4].markdown("**$ Total**")
    header_cols[5].markdown("**Remover**")

    for idx, item in enumerate(cart):
        col_codigo, col_nome, col_qtd, col_preco, col_total, col_remove = st.columns(
            [1.2, 3.5, 1, 1, 1, 0.8]
        )
        col_codigo.write(item["codigo"])
        col_nome.write(item["nome"])
        nova_qtd = col_qtd.number_input(
            "Quantidade",
            min_value=1,
            max_value=9999,
            value=int(item["quantidade"]),
            key=f"cart_qty_{idx}",
            label_visibility="collapsed",
        )
        if nova_qtd != item["quantidade"]:
            item["quantidade"] = int(nova_qtd)
            item["total"] = item["quantidade"] * item["preco_unitario"]

        col_preco.write(format_currency(item["preco_unitario"]))
        col_total.write(format_currency(item["total"]))

        if col_remove.button("🗑️", key=f"remove_{idx}"):
            st.session_state.cart.pop(idx)
            st.rerun()

    total = sum(entry["total"] for entry in cart)
    st.metric("Total do pedido", format_currency(total))


def build_cart_rows(destino: str) -> pd.DataFrame:
    setor = st.session_state.selected_setor
    cart = st.session_state.cart
    if not setor:
        st.warning("Selecione um setor antes de salvar o pedido.")
        return pd.DataFrame()
    if not cart:
        st.warning("Adicione itens ao carrinho antes de salvar.")
        return pd.DataFrame()

    linhas = []
    for item in cart:
        linhas.append(
            {
                "CòdClienteImpakto": COD_CLIENTE_IMPAKTO,
                "CódProImpakto": item["codigo"],
                "Item": item["nome"],
                "Qtde": int(item["quantidade"]),
                "$ Unitário": float(item["preco_unitario"]),
                "$ Total": float(item["total"]),
                "Unidade": setor["codigo"],
                "Setor": setor["codigo"],
                "SETOR2": setor["descricao"],
            }
        )
    return pd.DataFrame(linhas)


def persist_cart(destino: str) -> None:
    linhas = build_cart_rows(destino)
    if linhas.empty:
        return

    # Generate PDF for storage
    pdf_buffer = generate_previa_pdf()
    
    if firestore_enabled():
        status = "aguardando" if destino == "Aguardando Aprovação" else "pedido"
        save_rows_to_firestore(linhas, status, pdf_buffer)
        sync_firestore_to_session()
    else:
        destino_df = st.session_state.excel_data.get(destino, pd.DataFrame())
        destino_df = pd.concat([destino_df, linhas], ignore_index=True)
        st.session_state.excel_data[destino] = destino_df
    
    st.success(f"✅ Pedido do cliente '{st.session_state.selected_setor.get('descricao', 'cliente')}' salvo com sucesso!")
    st.session_state.cart = []
    st.success(
        f"{len(linhas)} item(ns) salvo(s) em '{destino}'. Atualize a aba correspondente para visualizar."
    )


def generate_previa_pdf() -> Optional[io.BytesIO]:
    cart = st.session_state.cart
    setor = st.session_state.selected_setor
    if not cart or not setor:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a1a"),
    )
    elements.append(Paragraph("<b>PRÉVIA DE PEDIDO - IMPAKTO</b>", title_style))
    elements.append(Spacer(1, 12))

    info_table = Table(
        [
            ["Data:", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Cliente:", str(COD_CLIENTE_IMPAKTO)],
            ["Setor:", setor["label"]],
            ["Itens:", str(len(cart))],
        ],
        colWidths=[3.5 * 28.35, 10 * 28.35],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    data = [["Código", "Produto", "Qtde", "Valor Unit.", "Total"]]
    total_pedido = 0.0
    for item in cart:
        data.append(
            [
                item["codigo"],
                item["nome"],
                str(item["quantidade"]),
                format_currency(item["preco_unitario"]),
                format_currency(item["total"]),
            ]
        )
        total_pedido += item["total"]

    data.append(["", "", "", "TOTAL", format_currency(total_pedido)])

    table = Table(data, colWidths=[2.5 * 28.35, 8 * 28.35, 1.5 * 28.35, 3 * 28.35, 3 * 28.35])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -2), 0.3, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F2F2F2")]),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, colors.black),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 10))

    note_style = ParagraphStyle(
        "Nota",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
    )
    elements.append(
        Paragraph(
            "<i>Documento gerado automaticamente. Confirme o pedido antes de enviar.</i>",
            note_style,
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer


def render_previa_download() -> None:
    pdf_buffer = generate_previa_pdf()
    if pdf_buffer is None:
        return

    st.info("📋 Prévia do pedido gerada")
    setor = st.session_state.selected_setor
    file_name = f"PREVIA_Pedido_{setor['codigo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Baixar PDF (para imprimir)",
            data=pdf_buffer.getvalue(),
            file_name=file_name,
            mime="application/pdf",
            use_container_width=True,
        )
    with col2:
        st.caption("✅ Será também salvo no Storage ao clicar em 'Salvar'")


def render_save_buttons() -> None:
    col1, col2 = st.columns(2)
    disabled = not st.session_state.cart or not st.session_state.selected_setor
    if col1.button("Salvar em 'Aguardando Aprovação'", disabled=disabled):
        persist_cart("Aguardando Aprovação")
    if col2.button("Aprovar direto em 'Pedido'", disabled=disabled):
        persist_cart("Pedido")



def update_excel_snapshot() -> None:
    if st.session_state.excel_data is None:
        return
    if firestore_enabled():
        sync_firestore_to_session()
    buffer = build_workbook_bytes(st.session_state.excel_data)
    st.session_state.excel_bytes = buffer.getvalue()


def render_download_section() -> None:
    if st.session_state.excel_data is None:
        return

    update_excel_snapshot()
    st.divider()
    st.subheader("Exportar planilha atualizada")
    excel_bytes = st.session_state.excel_bytes
    file_name = f"planilha_pedidos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    st.download_button(
        "Baixar Excel atualizado",
        data=excel_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    storage_path = get_storage_path()
    if storage_path:
        if st.button("Sobrescrever arquivo no servidor", use_container_width=True):
            dir_name = os.path.dirname(storage_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(storage_path, "wb") as handler:
                handler.write(excel_bytes)
            st.success(f"Arquivo salvo em {storage_path}")


def render_aguardando_tab() -> None:
    if firestore_enabled():
        sync_firestore_to_session()

    df = st.session_state.excel_data.get("Aguardando Aprovação", pd.DataFrame())
    st.subheader("📋 Pedidos aguardando aprovação")
    if df.empty:
        st.info("Nenhum item aguardando aprovação.")
        return

    # Group by client
    by_client = df.groupby("SETOR2")
    
    st.write(f"**Total: {len(by_client)} cliente(s) com {len(df)} item(ns)**")
    st.divider()
    
    for client, group_df in by_client:
        # Create card container
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1, 1, 1])
            
            # Client info
            with col1:
                st.markdown(f"### 🏢 {client}")
                st.caption(f"📊 {len(group_df)} item(ns) | 💰 Total: R$ {group_df['$ Total'].sum():.2f}")
            
            # Status badge
            with col2:
                st.metric("Status", "⏳ Pendente", delta=None)
            
            # Buttons
            with col3:
                if st.button("✏️", key=f"edit_{client}", help="Alterar"):
                    if st.session_state.get("edit_client") == client:
                        st.session_state.edit_client = None
                    else:
                        st.session_state.edit_client = client

            with col4:
                if st.button(f"✅", key=f"approve_{client}", help="Aprovar"):
                    if firestore_enabled():
                        db = get_firestore_client()
                        for idx in group_df.index:
                            doc_id = df.loc[idx, "__doc_id"]
                            original_data = df.loc[idx].to_dict()
                            
                            db.collection(FIRESTORE_COLLECTION).document(doc_id).update({
                                "status": "pedido",
                                "approved_by": st.session_state.get("current_user", "unknown"),
                                "approved_at": firestore.SERVER_TIMESTAMP,
                                "updated_at": firestore.SERVER_TIMESTAMP,
                            })
                            
                            # Log audit trail
                            log_audit("order_approved", {
                                "doc_id": doc_id,
                                "client": client,
                                "items_count": len(group_df),
                                "total_value": group_df["$ Total"].sum(),
                            })
                        
                        sync_firestore_to_session()
                    st.success(f"✅ Pedido de {client} aprovado! (Usuário: {st.session_state.get('current_user', 'unknown')})")
                    st.rerun()
            
            with col5:
                if st.button(f"❌", key=f"reject_{client}", help="Rejeitar"):
                    if firestore_enabled():
                        db = get_firestore_client()
                        for idx in group_df.index:
                            doc_id = df.loc[idx, "__doc_id"]
                            db.collection(FIRESTORE_COLLECTION).document(doc_id).delete()
                        sync_firestore_to_session()
                    st.warning(f"❌ Pedido de {client} removido!")
                    st.rerun()
            
            st.divider()
            
            # Items table
            st.write("**Items:**")
            items_display = group_df[[
                "CódProImpakto",
                "Item",
                "Qtde", 
                "$ Unitário",
                "$ Total",
                "Unidade"
            ]].copy()
            items_display.columns = ["📦 Código", "📝 Produto", "🔢 Qtde", "💵 Unit.", "💰 Total", "📐 Un."]
            st.dataframe(items_display, use_container_width=True, hide_index=True)
            
            # Edit section
            is_expanded = st.session_state.get("edit_client") == client
            with st.expander("✏️ Editar pedido", expanded=is_expanded):
                st.markdown("**Itens atuais (editar):**")
                st.caption("Edite o produto e a quantidade e clique em salvar.")

                editor_source = group_df[["CódProImpakto", "Item", "Qtde", "__doc_id"]].copy()
                editor_source["Produto"] = editor_source.apply(
                    lambda row: f"{row['CódProImpakto']} - {row['Item']}", axis=1
                )
                editor_display = editor_source[["Produto", "Qtde"]].reset_index(drop=True)
                doc_ids = editor_source["__doc_id"].tolist()

                produtos_df = st.session_state.excel_data.get("Produtos", pd.DataFrame()).copy()
                if not produtos_df.empty:
                    produtos_df["price"] = pd.to_numeric(
                        produtos_df.get("price"), errors="coerce"
                    ).fillna(0.0)
                    produtos_df["label"] = produtos_df.apply(
                        lambda row: f"{row['productCode']} - {row['name']}", axis=1
                    )
                    produto_options = produtos_df["label"].tolist()
                    produtos_map = {
                        row["label"]: row for _, row in produtos_df.iterrows()
                    }
                else:
                    produto_options = []
                    produtos_map = {}

                if produto_options:
                    produto_column = st.column_config.SelectboxColumn(
                        "Produto",
                        options=produto_options,
                        required=True,
                    )
                else:
                    produto_column = st.column_config.TextColumn("Produto")

                edited_df = st.data_editor(
                    editor_display,
                    column_config={
                        "Produto": produto_column,
                        "Qtde": st.column_config.NumberColumn(
                            "Qtde",
                            min_value=1,
                            step=1,
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_{client}",
                )

                edited_total = 0.0
                for _, row in edited_df.iterrows():
                    label = row.get("Produto")
                    qtde = parse_int(row.get("Qtde"))
                    produto = produtos_map.get(label)
                    if produto is not None:
                        edited_total += parse_float(produto.get("price")) * qtde
                st.metric("Total (previa)", format_currency(edited_total))

                if st.button("💾 Salvar alteracoes", key=f"save_edit_{client}"):
                    if firestore_enabled():
                        db = get_firestore_client()
                        for row_idx, row in edited_df.iterrows():
                            doc_id = doc_ids[row_idx]
                            label = row.get("Produto")
                            qtde = parse_int(row.get("Qtde"))
                            produto = produtos_map.get(label)
                            if not produto:
                                continue
                            preco = parse_float(produto.get("price"))
                            codigo = str(produto.get("productCode"))
                            nome = str(produto.get("name"))
                            db.collection(FIRESTORE_COLLECTION).document(doc_id).update({
                                "CódProImpakto": codigo,
                                "Item": nome,
                                "Qtde": qtde,
                                "$ Unitário": preco,
                                "$ Total": preco * qtde,
                                "updated_at": firestore.SERVER_TIMESTAMP,
                            })
                        sync_firestore_to_session()
                    st.success("✅ Alteracoes salvas!")
                    st.rerun()

                st.divider()

                col_remove, col_add = st.columns([1, 1])
                with col_remove:
                    with st.container(border=True):
                        st.markdown("**Remover itens:**")
                        items_to_remove = st.multiselect(
                            "Selecione itens para remover",
                            group_df.index,
                            format_func=lambda idx: f"🗑️ {df.loc[idx, 'Item']} (Qtde: {df.loc[idx, 'Qtde']})",
                            key=f"remove_{client}",
                            label_visibility="collapsed",
                        )

                        if items_to_remove and st.button(
                            "🗑️ Remover selecionados",
                            key=f"confirm_remove_{client}",
                            use_container_width=True,
                        ):
                            if firestore_enabled():
                                db = get_firestore_client()
                                for idx in items_to_remove:
                                    doc_id = df.loc[idx, "__doc_id"]
                                    db.collection(FIRESTORE_COLLECTION).document(doc_id).delete()
                                sync_firestore_to_session()
                            st.success("✅ Itens removidos!")
                            st.rerun()

                with col_add:
                    with st.container(border=True):
                        st.markdown("**Adicionar itens:**")
                        produtos_list = st.session_state.excel_data.get("Produtos", pd.DataFrame()).copy()
                        new_produto_label = None
                        produtos_map = {}
                        if not produtos_list.empty:
                            produtos_list["price"] = pd.to_numeric(
                                produtos_list.get("price"), errors="coerce"
                            ).fillna(0.0)
                            produtos_list["label"] = produtos_list.apply(
                                lambda row: f"{row['productCode']} - {row['name']}", axis=1
                            )
                            produtos_map = {
                                row["label"]: row for _, row in produtos_list.iterrows()
                            }
                            busca = st.text_input(
                                "Buscar produto (codigo ou nome)",
                                key=f"search_add_{client}",
                                label_visibility="collapsed",
                            )
                            if busca:
                                busca_lower = busca.lower()
                                produtos_list = produtos_list[
                                    produtos_list["name"].astype(str).str.lower().str.contains(busca_lower)
                                    | produtos_list["productCode"].astype(str).str.lower().str.contains(busca_lower)
                                ]
                            if not produtos_list.empty:
                                new_produto_label = st.selectbox(
                                    "Produto",
                                    produtos_list["label"].tolist(),
                                    key=f"new_produto_{client}",
                                    label_visibility="collapsed",
                                )
                            else:
                                st.info("Nenhum produto encontrado com esse filtro.")
                        else:
                            st.warning("Lista de produtos vazia.")

                        new_qtde = st.number_input(
                            "Quantidade",
                            min_value=1,
                            value=1,
                            key=f"new_qtde_{client}",
                            label_visibility="collapsed",
                        )

                        if new_produto_label and st.button(
                            "➕ Adicionar",
                            key=f"add_item_{client}",
                            use_container_width=True,
                        ):
                            produto = produtos_map.get(new_produto_label)
                            if produto is None:
                                st.error("❌ Produto invalido.")
                            else:
                                template = group_df.iloc[0].to_dict()
                                novo_item = template.copy()
                                novo_item["CódProImpakto"] = str(produto.get("productCode"))
                                novo_item["Item"] = str(produto.get("name"))
                                novo_item["Qtde"] = new_qtde
                                novo_item["$ Unitário"] = parse_float(produto.get("price"))
                                novo_item["$ Total"] = parse_float(produto.get("price")) * new_qtde
                                novo_item["status"] = "aguardando"

                                if "__doc_id" in novo_item:
                                    del novo_item["__doc_id"]

                                if firestore_enabled():
                                    db = get_firestore_client()
                                    db.collection(FIRESTORE_COLLECTION).add(novo_item)
                                    sync_firestore_to_session()

                                st.success("✅ Item adicionado!")
                                st.rerun()
            
            st.write("")  # Spacing


def render_new_order_tab() -> None:
    data = st.session_state.excel_data
    if data is None:
        st.info("Carregue uma planilha para começar.")
        return
    
    # Só sincroniza com Firestore se há dados lá (evita sobrescrever com DataFrames vazios)
    if firestore_enabled():
        produtos_firestore = fetch_products_df()
        setores_firestore = fetch_setores_df()
        if not produtos_firestore.empty and not setores_firestore.empty:
            data["Produtos"] = produtos_firestore
            data["Setor"] = setores_firestore

    st.subheader("Novo pedido")
    render_setor_selector(data.get("Setor", pd.DataFrame()))
    produto = render_product_selector(data.get("Produtos", pd.DataFrame()))

    col_qtd, col_add = st.columns([1, 1])
    quantidade = col_qtd.number_input(
        "Quantidade",
        min_value=1,
        max_value=9999,
        value=1,
        step=1,
    )
    can_add = produto is not None and st.session_state.selected_setor is not None
    if col_add.button("Adicionar ao carrinho", disabled=not can_add):
        add_item_to_cart(produto, int(quantidade))
        st.success("Produto adicionado ao carrinho.")

    render_cart()
    render_previa_download()
    render_save_buttons()


def render_approved_orders_tab() -> None:
    """Exibe pedidos aprovados com histórico de auditoria completo."""
    st.subheader("📋 Pedidos Aprovados - Histórico")
    
    try:
        db = get_firestore_client()
        
        # Fetch approved orders
        try:
            approved_orders = db.collection(FIRESTORE_COLLECTION)\
                .where("status", "==", "pedido")\
                .order_by("approved_at", direction=firestore.Query.DESCENDING)\
                .stream()

            orders_list = []
            for doc in approved_orders:
                order_data = doc.to_dict()
                order_data["__doc_id"] = doc.id
                orders_list.append(order_data)
        except Exception as exc:
            st.warning(
                "⚠️ Índice não encontrado no Firestore. "
                "Carregando sem ordenação (fallback local)."
            )
            approved_orders = db.collection(FIRESTORE_COLLECTION)\
                .where("status", "==", "pedido")\
                .stream()

            orders_list = []
            for doc in approved_orders:
                order_data = doc.to_dict()
                order_data["__doc_id"] = doc.id
                orders_list.append(order_data)

            def sort_key(item: Dict) -> datetime:
                value = item.get("approved_at")
                if hasattr(value, "to_datetime"):
                    return value.to_datetime()
                if isinstance(value, datetime):
                    return value
                return datetime.min

            orders_list.sort(key=sort_key, reverse=True)
        
        if not orders_list:
            st.info("ℹ️ Nenhum pedido aprovado ainda.")
            return
        
        # Group by client
        orders_df = pd.DataFrame(orders_list)
        grouped = orders_df.groupby("Setor")
        
        for client, group_df in grouped:
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 1, 1])
                col1.markdown(f"**👤 {client}**")
                col2.metric("Pedidos", len(group_df))
                col3.metric("Total", f"R$ {group_df['$ Total'].sum():.2f}")
                
                # Display each approved order
                for idx, order in group_df.iterrows():
                    with st.expander(f"📦 Pedido #{idx + 1} - Aprovado em {order.get('approved_at', 'N/A')}"):
                        col_info, col_user = st.columns([3, 1])
                        
                        with col_info:
                            st.write("**Informações:**")
                            st.write(f"- Criado em: {order.get('created_at', 'N/A')}")
                            st.write(f"- Aprovado em: {order.get('approved_at', 'N/A')}")
                            st.write(f"- Total: R$ {order.get('$ Total', 0):.2f}")
                        
                        with col_user:
                            st.write("**Aprovado por:**")
                            st.write(f"👤 {order.get('approved_by', 'unknown')}")
                        
                        # Fetch and display audit trail
                        st.write("**Histórico de Auditoria:**")
                        audit_docs = db.collection(FIRESTORE_AUDIT_COLLECTION)\
                            .where("doc_id", "==", order.get("__doc_id"))\
                            .stream()
                        
                        audit_list = []
                        for audit_doc in audit_docs:
                            audit_data = audit_doc.to_dict()
                            audit_list.append(audit_data)
                        
                        if audit_list:
                            audit_df = pd.DataFrame(audit_list)
                            for _, audit_row in audit_df.iterrows():
                                st.write(f"- **{audit_row.get('action')}** por {audit_row.get('username')} em {audit_row.get('timestamp')}")
                                if audit_row.get('details'):
                                    st.json(audit_row.get('details'))
                        else:
                            st.write("- Nenhum registro de auditoria disponível")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar pedidos aprovados: {e}")


def render_user_management_tab() -> None:
    """Admin interface for user management."""
    st.subheader("👥 Gerenciamento de Usuários")
    
    # Check if current user is admin
    if st.session_state.get("current_user") != "admin":
        st.warning("⚠️ Apenas admins podem gerenciar usuários.")
        return
    
    # Tab: Create, List, Edit
    tab_create, tab_list, tab_edit = st.tabs(["➕ Criar Usuário", "📋 Listar Usuários", "✏️ Editar Usuário"])
    
    # TAB 1: Create User
    with tab_create:
        st.markdown("#### Criar Novo Usuário")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            new_username = st.text_input("👤 Nome de usuário")
        with col2:
            new_role = st.selectbox("📌 Função", ["user", "admin"])
        
        new_password = st.text_input("🔑 Senha", type="password")
        confirm_password = st.text_input("🔑 Confirmar Senha", type="password")
        
        if st.button("✅ Criar Usuário", use_container_width=True):
            if not new_username or not new_password:
                st.error("❌ Usuário e senha são obrigatórios.")
            elif new_password != confirm_password:
                st.error("❌ As senhas não correspondem.")
            else:
                if create_user(new_username, new_password, new_role):
                    st.balloons()
    
    # TAB 2: List Users
    with tab_list:
        st.markdown("#### Lista de Usuários")
        users = get_users_list()
        
        if not users:
            st.info("ℹ️ Nenhum usuário cadastrado.")
        else:
            users_df = pd.DataFrame(users)
            users_df = users_df[["username", "role", "created_at", "updated_at"]]
            st.dataframe(users_df, use_container_width=True, hide_index=True)
    
    # TAB 3: Edit User
    with tab_edit:
        st.markdown("#### Editar Usuário")
        users = get_users_list()
        
        if not users:
            st.info("ℹ️ Nenhum usuário para editar.")
        else:
            usernames = [u["username"] for u in users]
            selected_user = st.selectbox("👤 Selecione usuário", usernames)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("🔑 Redefinir Senha", use_container_width=True):
                    new_pwd = st.text_input("Nova Senha", type="password", key="reset_pwd")
                    confirm_pwd = st.text_input("Confirmar Senha", type="password", key="confirm_pwd")
                    
                    if st.button("✅ Atualizar Senha"):
                        if new_pwd != confirm_pwd:
                            st.error("❌ Senhas não correspondem.")
                        else:
                            update_user_password(selected_user, new_pwd)
            
            with col2:
                if st.button("🗑️ Deletar Usuário", use_container_width=True):
                    if st.warning(f"⚠️ Tem certeza que quer deletar '{selected_user}'?"):
                        if st.button("✅ Confirmar Deleção"):
                            delete_user(selected_user)
                            st.rerun()
            
            with col3:
                st.write("")  # Placeholder for alignment


def main() -> None:
    st.set_page_config(page_title="Sistema de Gestão de Pedidos", layout="wide")
    init_session_state()
    st.title("Sistema de Gestão de Pedidos - Versão Web")
    st.caption("Interface Streamlit preparada para deploy em serviços como Railway ou Render.")

    # Check authentication
    if not check_authentication():
        render_login()
        st.stop()
    
    # Display current user in sidebar
    with st.sidebar:
        st.write(f"👤 Usuário: **{st.session_state.current_user}**")
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()

    render_sidebar()

    if st.session_state.excel_data is None:
        st.stop()

    # Create tabs based on user role
    if st.session_state.get("current_user") == "admin":
        tab_novo, tab_aguardando, tab_aprovados, tab_usuarios = st.tabs([
            "Novo Pedido", 
            "Aguardando Aprovação", 
            "📋 Pedidos Aprovados",
            "👥 Gerenciar Usuários"
        ])
    else:
        tab_novo, tab_aguardando, tab_aprovados = st.tabs([
            "Novo Pedido", 
            "Aguardando Aprovação", 
            "📋 Pedidos Aprovados"
        ])
    
    with tab_novo:
        render_new_order_tab()
    with tab_aguardando:
        render_aguardando_tab()
    with tab_aprovados:
        render_approved_orders_tab()
    
    if st.session_state.get("current_user") == "admin":
        with tab_usuarios:
            render_user_management_tab()

    render_download_section()


if __name__ == "__main__":
    main()
