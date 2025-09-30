import streamlit as st
from datetime import datetime
import sqlite3
import pandas as pd

# ======================================================
# BANCO DE DADOS
# ======================================================
DB_FILE = "solicitacoes.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_from TEXT,
                country TEXT,
                model TEXT NOT NULL,
                cbu_ckd TEXT,
                date_request TEXT,
                requester TEXT,
                family TEXT,
                variant TEXT NOT NULL,
                legislacao TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                approved INTEGER DEFAULT 0
            )
        """)
        # Admin padrão
        conn.execute("""
            INSERT OR IGNORE INTO users (username, password, role, approved)
            VALUES ('admin', 'admin123', 'admin', 1)
        """)

def salvar_solicitacao(dados):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO solicitacoes
            (request_from, country, model, cbu_ckd, date_request, requester,
             family, variant, legislacao, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(dados.values()))

def listar_solicitacoes(f_pais=None, f_model=None):
    query = "SELECT * FROM solicitacoes WHERE 1=1"
    params = []
    if f_pais:
        query += " AND country LIKE ?"
        params.append(f"%{f_pais}%")
    if f_model:
        query += " AND model LIKE ?"
        params.append(f"%{f_model}%")
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(query, conn, params=params)

def atualizar_solicitacao(id_, dados):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            UPDATE solicitacoes
            SET request_from=?, country=?, model=?, cbu_ckd=?, date_request=?, 
                requester=?, family=?, variant=?, legislacao=?
            WHERE id=?
        """, (*dados.values(), id_))

def excluir_solicitacao(id_):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM solicitacoes WHERE id=?", (id_,))

# Usuários
def criar_usuario(username, password, role="creator"):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO users (username, password, role, approved)
            VALUES (?, ?, ?, 0)
        """, (username, password, role))

def listar_usuarios(pendentes=False):
    with sqlite3.connect(DB_FILE) as conn:
        if pendentes:
            return pd.read_sql_query("SELECT * FROM users WHERE approved=0", conn)
        return pd.read_sql_query("SELECT * FROM users", conn)

def aprovar_usuario(username, aprovar=True):
    with sqlite3.connect(DB_FILE) as conn:
        if aprovar:
            conn.execute("UPDATE users SET approved=1 WHERE username=?", (username,))
        else:
            conn.execute("DELETE FROM users WHERE username=?", (username,))

def editar_permissoes(username, novo_role):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE users SET role=? WHERE username=?", (novo_role, username))

def validar_usuario(user, pwd):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute(
            "SELECT role, approved FROM users WHERE username=? AND password=?",
            (user, pwd)
        ).fetchone()
        if row and row[1] == 1:
            return row[0]
        return None

# ======================================================
# APP STREAMLIT
# ======================================================
st.set_page_config(page_title="Sistema de Solicitações", page_icon="📋", layout="wide")
init_db()

if "auth_role" not in st.session_state:
    st.session_state.auth_role = None
if "username" not in st.session_state:
    st.session_state.username = None

# Login e Registro
if not st.session_state.auth_role:
    st.title("🔑 Solicitações C/P")

    # Abas para login e cadastro
    tab1, tab2 = st.tabs(["Entrar", "Criar Conta"])

    # Aba Login
    with tab1:
        with st.form("login_form"):
            st.subheader("Acesse sua conta")
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")

        if entrar:
            role = validar_usuario(user, pwd)
            if role:
                st.session_state.auth_role = role
                st.session_state.username = user
                st.rerun()
            else:
                st.error("❌ Credenciais inválidas ou conta não aprovada")

    # Aba Criar Conta
    with tab2:
        with st.form("register_form"):
            st.subheader("Criar nova conta")
            new_user = st.text_input("Novo Usuário")
            new_pwd = st.text_input("Nova Senha", type="password")
            criar = st.form_submit_button("Registrar")

        if criar:
            try:
                criar_usuario(new_user, new_pwd)
                st.success("✅ Usuário criado! Aguarde aprovação do Admin.")
            except:
                st.error("❌ Nome de usuário já existe.")

    st.stop()

# ======================================================
# MENU LATERAL
# ======================================================
st.sidebar.write(f"👤 Usuário: {st.session_state.username} ({st.session_state.auth_role})")

if st.session_state.auth_role == "admin":
    menu = st.sidebar.radio(
        "Navegação",
        [
            "Nova Solicitação",
            "Pesquisar Solicitações",
            "Gerenciar Solicitações",
            "Gerenciar Usuários",
        ],
        key="menu_admin"
    )

elif st.session_state.auth_role == "editor":
    menu = st.sidebar.radio(
        "Navegação",
        ["Nova Solicitação", "Pesquisar Solicitações"],
        key="menu_editor"
    )
elif st.session_state.auth_role == "creator":
    menu = st.sidebar.radio(
        "Navegação",
        ["Nova Solicitação"],
        key="menu_creator"
    )
else:  # viewer
    menu = st.sidebar.radio(
        "Navegação",
        ["Pesquisar Solicitações"],
        key="menu_viewer"
    )

# ======================================================
# NOVA SOLICITAÇÃO
# ======================================================
if menu == "Nova Solicitação":
    if st.session_state.auth_role not in ["admin", "editor", "creator"]:
        st.warning("Você não tem permissão para criar solicitações.")
        st.stop()

    st.title("📥 Nova Solicitação")

    with st.form("form_solicitacao"):
        col1, col2, col3 = st.columns(3)

        with col1:
            request_from = st.text_input("Request From")
            country = st.text_input("Country")
            model = st.text_input("Model *")
        with col2:
            cbu_ckd = st.text_input("CBU/CKD")
            date_request = st.date_input("Date Request", datetime.today())
            requester = st.text_input("Requester")
        with col3:
            family = st.text_input("Family")
            variant = st.text_input("Variant *").upper()
            legislacao = st.text_input("Legislação")

        submitted = st.form_submit_button("Salvar Solicitação")

    if submitted:
        if not model.strip() or not variant.strip():
            st.error("Campos obrigatórios (Model e Variant) devem ser preenchidos.")
        else:
            dados = {
                "request_from": request_from,
                "country": country,
                "model": model,
                "cbu_ckd": cbu_ckd,
                "date_request": date_request.strftime("%Y-%m-%d"),
                "requester": requester,
                "family": family,
                "variant": variant.upper(),
                "legislacao": legislacao,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            salvar_solicitacao(dados)
            st.success("✅ Solicitação salva!")
            st.balloons()
            st.rerun()

# ======================================================
# PESQUISAR SOLICITAÇÕES
# ======================================================
elif menu == "Pesquisar Solicitações":
    if st.session_state.auth_role not in ["admin", "editor", "viewer"]:
        st.warning("Você não tem permissão para pesquisar solicitações.")
        st.stop()

    st.title("🔍 Pesquisar Solicitações")

    colf1, colf2 = st.columns(2)
    with colf1:
        filtro_pais = st.text_input("Filtrar por país")
    with colf2:
        filtro_model = st.text_input("Filtrar por modelo")

    df = listar_solicitacoes(filtro_pais, filtro_model)
    st.dataframe(df)

# ======================================================
# GERENCIAR SOLICITAÇÕES
# ======================================================
elif menu == "Gerenciar Solicitações":
    if st.session_state.auth_role != "admin":
        st.warning("Apenas administradores podem editar/excluir solicitações.")
        st.stop()

    st.title("⚙️ Gerenciar Solicitações")

    df_all = listar_solicitacoes()
    if df_all.empty:
        st.info("Nenhuma solicitação registrada ainda.")
        st.stop()

    df_all["opcao"] = df_all.apply(
        lambda row: f"[{row['id']}] {row['variant']} – {row['country']}", axis=1
    )
    escolha = st.selectbox("Escolha uma solicitação", df_all["opcao"])
    id_escolhido = int(escolha.split("]")[0][1:])
    sol = df_all[df_all["id"] == id_escolhido].iloc[0]

    with st.form("editar_solicitacao"):
        col1, col2, col3 = st.columns(3)

        with col1:
            request_from = st.text_input("Request From", sol["request_from"])
            country = st.text_input("Country", sol["country"])
            model = st.text_input("Model *", sol["model"])
        with col2:
            cbu_ckd = st.text_input("CBU/CKD", sol["cbu_ckd"])
            date_request = st.text_input("Date Request", sol["date_request"])
            requester = st.text_input("Requester", sol["requester"])
        with col3:
            family = st.text_input("Family", sol["family"])
            variant = st.text_input("Variant *", sol["variant"]).upper()
            legislacao = st.text_input("Legislação", sol["legislacao"])

        atualizar = st.form_submit_button("💾 Atualizar")
        excluir = st.form_submit_button("🗑️ Excluir")

    if atualizar:
        dados = {
            "request_from": request_from,
            "country": country,
            "model": model,
            "cbu_ckd": cbu_ckd,
            "date_request": date_request,
            "requester": requester,
            "family": family,
            "variant": variant.upper(),
            "legislacao": legislacao
        }
        atualizar_solicitacao(id_escolhido, dados)
        st.success("✅ Solicitação atualizada!")
        st.rerun()

    if excluir:
        st.warning("⚠️ Confirma a exclusão? Essa ação não pode ser desfeita.")
        if st.checkbox("Sim, desejo excluir permanentemente"):
            excluir_solicitacao(id_escolhido)
            st.success("🗑️ Solicitação excluída!")
            st.rerun()

# ======================================================
# 👥 GERENCIAR USUÁRIOS
# ======================================================
elif menu == "Gerenciar Usuários":
    if st.session_state.auth_role != "admin":
        st.warning("Apenas administradores podem acessar esta área.")
        st.stop()

    st.title("👥 Gerenciar Usuários")
    tabs = st.tabs(["Todos Usuários", "Pendentes"])

    # --------------------------------------------
    # 🧑‍💻 Aba: Todos Usuários
    # --------------------------------------------
    with tabs[0]:
        todos = listar_usuarios()
        if todos.empty:
            st.info("Nenhum usuário cadastrado ainda.")
        else:
            st.dataframe(todos, use_container_width=True)

            # Caixas lado a lado para mudar permissão
            col1, col2 = st.columns(2)
            with col1:
                user_sel = st.selectbox("Selecionar usuário", todos["username"])
            with col2:
                novo_role = st.selectbox("Nova permissão", ["admin", "viewer", "editor", "creator"])

            # Botão centralizado
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Atualizar Permissão"):
                editar_permissoes(user_sel, novo_role)
                st.success(f"✅ Permissão de {user_sel} alterada para {novo_role}")
                st.rerun()

    # --------------------------------------------
    # 📝 Aba: Pendentes
    # --------------------------------------------
    with tabs[1]:
        pendentes = listar_usuarios(pendentes=True)
        if pendentes.empty:
            st.info("Nenhum usuário pendente de aprovação.")
        else:
            for _, row in pendentes.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(f"🔒 {row['username']} ({row['role']})")
                if col2.button("Aprovar", key=f"ap_{row['username']}"):
                    aprovar_usuario(row['username'], True)
                    st.success(f"✅ Usuário {row['username']} aprovado!")
                    st.rerun()
                if col3.button("Recusar", key=f"rc_{row['username']}"):
                    aprovar_usuario(row['username'], False)
                    st.warning(f"🚫 Usuário {row['username']} recusado!")
                    st.rerun()
