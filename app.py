import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import hashlib
from PIL import Image
import io
from supabase import create_client, Client

st.set_page_config(
    page_title="Contrôle Financier",
    page_icon="💶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuração da Conexão com o Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["https://zrabayrovzbkbdbjeuor.supabase.co"]
    key = st.secrets["sb_secret_PaTy9z_z1eH2jxkV8m6_g_5sAUvBUR"]
    return create_client(url, key)

supabase = init_connection()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    if make_hash(password) == hashed_text:
        return True
    return False

# Função para cadastrar usuário no Supabase
def add_user(username, nome_completo, senha):
    try:
        hashed_password = make_hash(senha)
        data = {
            "username": username,
            "nome_completo": nome_completo,
            "senha": hashed_password
        }
        supabase.table("usuarios").insert(data).execute()
        return True
    except Exception as e:
        return False

# Função para verificar login no Supabase
def login_user(username, senha):
    try:
        response = supabase.table("usuarios").select("*").eq("username", username).execute()
        user = response.data
        if user:
            stored_password = user[0]["senha"]
            if check_hash(senha, stored_password):
                return user[0]
        return None
    except Exception as e:
        return None

# Função para buscar lançamentos do usuário
def carregar_lancamentos(username):
    try:
        response = supabase.table("lancamentos").select("*").eq("username", username).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame(columns=["id", "username", "data", "descricao", "categoria", "tipo", "valor", "contexto"])
    except Exception as e:
        return pd.DataFrame(columns=["id", "username", "data", "descricao", "categoria", "tipo", "valor", "contexto"])

# Função para salvar lançamento no Supabase
def salvar_lancamento(username, data, descricao, categoria, tipo, valor, contexto):
    try:
        data_dict = {
            "username": username,
            "data": str(data),
            "descricao": descricao,
            "categoria": categoria,
            "tipo": tipo,
            "valor": float(valor),
            "contexto": contexto
        }
        supabase.table("lancamentos").insert(data_dict).execute()
        return True
    except Exception as e:
        return False

# Controle de Sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user' not in st.session_state:
    st.session_state['user'] = None

# Tela de Login e Cadastro se não estiver logado
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>Accès au Contrôle Financier</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Connectez-vous ou créez un compte.</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Connexion", "📝 S'inscrire"])
    
    with tab1:
        st.subheader("Connexion")
        username_login = st.text_input("Utilisateur (E-mail ou Pseudo)", key="login_user")
        senha_login = st.text_input("Mot de passe", type="password", key="login_pass")
        
        if st.button("Se connecter"):
            user_data = login_user(username_login, senha_login)
            if user_data:
                st.session_state['logged_in'] = True
                st.session_state['user'] = user_data
                st.rerun()
            else:
                st.error("Utilisateur ou mot de passe incorrect.")
                
    with tab2:
        st.subheader("Créer un compte")
        new_user = st.text_input("Définir un nom d'utilisateur", key="reg_user")
        new_name = st.text_input("Votre Nom Complet", key="reg_name")
        new_pass = st.text_input("Choisir un mot de passe", type="password", key="reg_pass")
        
        if st.button("Créer le compte"):
            if new_user and new_name and new_pass:
                sucesso = add_user(new_user, new_name, new_pass)
                if sucesso:
                    st.success("Compte créé avec succès! Vous pouvez vous connecter.")
                else:
                    st.error("Cet utilisateur existe déjà ou une erreur est survenue.")
            else:
                st.warning("Veuillez remplir tous les champs.")

else:
    # Área interna do aplicativo após o login
    user_info = st.session_state['user']
    st.sidebar.title(f"Bienvenue, {user_info.get('nome_completo', user_info['username'])}")
    
    if st.sidebar.button("Se déconnecter"):
        st.session_state['logged_in'] = False
        st.session_state['user'] = None
        st.rerun()
        
    st.title("💶 Tableau de Bord Financier")
    
    # Carrega dados do Supabase
    df_lancamentos = carregar_lancamentos(user_info['username'])
    
    menu = st.sidebar.selectbox("Navigation", ["Lancements", "Tableau de Bord"])
    
    if menu == "Lancements":
        st.subheader("Ajouter un nouveau lancement")
        with st.form("form_lancamento"):
            col1, col2 = st.columns(2)
            with col1:
                data = st.date_input("Date", datetime.today())
                tipo = st.selectbox("Type", ["Revenu", "Dépense"])
                valor = st.number_input("Montant", min_value=0.0, format="%.2f")
            with col2:
                categoria = st.text_input("Catégorie")
                contexto = st.text_input("Contexte / Compte")
            
            descricao = st.text_input("Description")
            
            submitted = st.form_submit_button("Enregistrer")
            if submitted:
                if descricao and categoria:
                    ok = salvar_lancamento(user_info['username'], data, descricao, categoria, tipo, valor, contexto)
                    if ok:
                        st.success("Lancement enregistré avec succès dans le Cloud!")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement.")
                else:
                    st.warning("Veuillez remplir les champs obligatoires.")
                    
        st.subheader("Historique des Lancements")
        if not df_lancamentos.empty:
            st.dataframe(df_lancamentos, use_container_width=True)
        else:
            st.info("Aucun lancement enregistré pour le moment.")
            
    elif menu == "Tableau de Bord":
        st.subheader("Résumé Financier")
        if not df_lancamentos.empty:
            total_receitas = df_lancamentos[df_lancamentos['tipo'] == 'Revenu']['valor'].sum()
            total_despesas = df_lancamentos[df_lancamentos['tipo'] == 'Dépense']['valor'].sum()
            saldo = total_receitas - total_despesas
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Revenus", f"{total_receitas:.2f} €")
            col2.metric("Total Dépenses", f"{total_despesas:.2f} €")
            col3.metric("Solde", f"{saldo:.2f} €")
        else:
            st.info("Ajoutez des lancements pour voir le tableau de bord.")
