import streamlit as st
from supabase import create_client, Client
import hashlib

# Configuração da página
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💰",
    layout="centered"
)

# Estilização visual básica via CSS para combinar com o tema escuro
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stTextInput > div > div > input {
        background-color: #1a1c23;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# Função para inicializar a conexão com o Supabase de forma segura
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro crítico de configuração ou conexão: {e}")
        return None

supabase = init_supabase()

# Função auxiliar para criptografar senha com MD5 (ou substitua pelo seu método atual)
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Controle de sessão do usuário
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- TELA PRINCIPAL DE AUTENTICAÇÃO ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>Acesso ao Controle Financeiro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Entre com sua conta ou cadastre-se com seu nome completo.</p>", unsafe_allow_html=True)
    
    tab_entrar, tab_criar = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
    
    # Aba de Login
    with tab_entrar:
        st.markdown("### Entrar no Sistema")
        login_user = st.text_input("Usuário (E-mail ou Apelido)", key="login_user_input")
        login_pass = st.text_input("Senha", type="password", key="login_pass_input")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if not supabase:
                st.error("Erro: Conexão com o Supabase indisponível.")
            elif not login_user or not login_pass:
                st.warning("Preencha todos os campos.")
            else:
                try:
                    # Consulta na tabela 'usuarios' do Supabase
                    response = supabase.table("usuarios").select("*").eq("username", login_user).execute()
                    usuarios = response.data
                    
                    if usuarios and len(usuarios) > 0:
                        user_db = usuarios[0]
                        senha_hash = hash_password(login_pass)
                        
                        if user_db.get("senha") == senha_hash:
                            st.session_state.logged_in = True
                            st.session_state.username = user_db.get("username")
                            st.session_state.nome_completo = user_db.get("nome", "")
                            st.success("Login realizado com sucesso! Carregando...")
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception as e:
                    st.error(f"Erro ao autenticar: {e}")

    # Aba de Cadastro
    with tab_criar:
        st.markdown("### Criar Nova Conta")
        novo_user = st.text_input("Defina um Usuário de Login (ex: seu e-mail)", key="novo_user_input")
        novo_nome = st.text_input("Seu Nome Completo", key="novo_nome_input")
        novo_pass = st.text_input("Escolha uma Senha", type="password", key="novo_pass_input")
        
        if st.button("Cadastrar Nova Conta", use_container_width=True):
            if not supabase:
                st.error("Erro: Conexão com o Supabase indisponível.")
            elif not novo_user or not novo_nome or not novo_pass:
                st.warning("Preencha todos os campos para o cadastro.")
            else:
                try:
                    # Verifica se o usuário já existe
                    check_resp = supabase.table("usuarios").select("*").eq("username", novo_user).execute()
                    if check_resp.data and len(check_resp.data) > 0:
                        st.error("Este usuário já existe ou ocorreu uma falha no cadastro.")
                    else:
                        # Insere o novo usuário com senha protegida
                        senha_hash = hash_password(novo_pass)
                        insert_resp = supabase.table("usuarios").insert({
                            "username": novo_user,
                            "nome": novo_nome,
                            "senha": senha_hash
                        }).execute()
                        
                        if insert_resp.data:
                            st.success("Conta cadastrada com sucesso! Vá para a aba 'Entrar'.")
                        else:
                            st.error("Erro ao registrar usuário no banco de dados.")
                except Exception as e:
                    st.error(f"Erro ao cadastrar usuário: {e}")

# --- DASHBOARD DO USUÁRIO LOGADO ---
else:
    st.title(f"Bem-vindo, {st.session_state.get('nome_completo', st.session_state.username)}! 📊")
    st.write("Seu controle financeiro está conectado com segurança ao Supabase.")
    
    # Exemplo de conteúdo do painel financeiro
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Saldo Atual", "R$ 0,00", "0.0%")
    with col2:
        st.metric("Receitas do Mês", "R$ 0,00", "0.0%")
    with col3:
        st.metric("Despesas do Mês", "R$ 0,00", "0.0%")
        
    st.divider()
    
    if st.button("Sair da Conta (Logout)"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
