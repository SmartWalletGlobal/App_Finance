import datetime
import hashlib
import io
import pandas as pd
from PIL import Image
import plotly.express as px
import streamlit as st
from supabase import Client, create_client

# --- CONEXÃO COM O SUPABASE (NUVEM) ---
SUPABASE_URL = "https://zrabayrovzbkbdbjeuor.supabase.co"
SUPABASE_KEY = "sb_secret_PaTy9z_z1eH2jxkV8m6_g_5sAUvBUR"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# --------------------------------------

st.set_page_config(
    page_title="Controle Financeiro | Multi-Usuário",
    page_icon="💶",
    layout="centered",
    initial_sidebar_state="expanded",
)

# --- CONFIGURAÇÃO PWA E META TAGS PARA O CELULAR ---
st.markdown(
    """
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="Finanças">
        <meta name="theme-color" content="#0e1117">
        <link rel="manifest" href="data:application/manifest+json;charset=utf-8,{
            \"name\": \"Controle Financeiro\",
            \"short_name\": \"Finanças\",
            \"start_url\": \"./\",
            \"display\": \"standalone\",
            \"background_color\": \"#0e1117\",
            \"theme_color\": \"#0e1117\",
            \"icons\": [
                {
                    \"src\": \"https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=512&auto=format&fit=crop\",
                    \"sizes\": \"512x512\",
                    \"type\": \"image/jpeg\"
                }
            ]
        }">
        <link rel="apple-touch-icon" href="https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=512&auto=format&fit=crop">
    </head>
""",
    unsafe_allow_html=True,
)


def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text


# --- FUNÇÕES DE BANCO DE DADOS (SUPABASE) COM TRATAMENTO DE ERROS CLARO ---

def cadastrar_usuario(username, nome_completo, senha):
    try:
        res = supabase.table("usuarios").select("username").eq("username", username).execute()
        if res.data and len(res.data) > 0:
            return False, "Este usuário já existe."
        
        # Tenta inserir considerando diferentes variações de nomes de colunas comuns
        try:
            supabase.table("usuarios").insert({
                "username": username,
                "nome_completo": nome_completo,
                "senha": make_hash(senha),
            }).execute()
        except Exception:
            supabase.table("usuarios").insert({
                "username": username,
                "nome": nome_completo,
                "senha": make_hash(senha),
            }).execute()
        return True, ""
    except Exception as e:
        return False, str(e)


def autenticar_usuario(username, senha):
    try:
        res = supabase.table("usuarios").select("senha").eq("username", username).execute()
        if res.data and len(res.data) > 0:
            stored_pass = res.data[0]["senha"]
            return check_hash(senha, stored_pass), ""
        return False, "Usuário não encontrado."
    except Exception as e:
        return False, str(e)


def obter_dados_usuario(username):
    try:
        res = supabase.table("usuarios").select("*").eq("username", username).execute()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            nome = row.get("nome_completo") or row.get("nome") or row.get("full_name") or username
            endereco = row.get("endereco") or row.get("address") or ""
            foto = row.get("foto_perfil") or row.get("foto") or None
            
            if foto and isinstance(foto, str):
                import base64
                try:
                    foto = base64.b64decode(foto)
                except Exception:
                    pass
            return (nome, endereco, foto)
        return (username, "", None)
    except Exception:
        return (username, "", None)


def atualizar_perfil(username, novo_nome, novo_endereco, nova_senha, nova_foto_blob, remover_foto=False):
    try:
        update_data = {"nome_completo": novo_nome, "endereco": novo_endereco}
        if nova_senha:
            update_data["senha"] = make_hash(nova_senha)

        if remover_foto:
            update_data["foto_perfil"] = None
        elif nova_foto_blob is not None:
            import base64
            update_data["foto_perfil"] = base64.b64encode(nova_foto_blob).decode("utf-8")

        try:
            supabase.table("usuarios").update(update_data).eq("username", username).execute()
        except Exception:
            update_data["nome"] = novo_nome
            update_data.pop("nome_completo", None)
            supabase.table("usuarios").update(update_data).eq("username", username).execute()
        return True, ""
    except Exception as e:
        return False, str(e)


def carregar_dados(username):
    try:
        res = supabase.table("lancamentos").select("*").eq("username", username).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            if "contexto" not in df.columns:
                df["contexto"] = "Pessoal"
            return df
        return pd.DataFrame(columns=["id", "username", "data", "descricao", "categoria", "tipo", "valor", "contexto"])
    except Exception:
        return pd.DataFrame(columns=["id", "username", "data", "descricao", "categoria", "tipo", "valor", "contexto"])


def salvar_lancamento(username, data, descricao, categoria, tipo, valor, contexto):
    try:
        supabase.table("lancamentos").insert({
            "username": username,
            "data": str(data),
            "descricao": descricao,
            "categoria": categoria,
            "tipo": tipo,
            "valor": float(valor),
            "contexto": contexto,
        }).execute()
        return True
    except Exception:
        return False


def deletar_lancamento(id_lancamento, username):
    try:
        supabase.table("lancamentos").delete().eq("id", id_lancamento).eq("username", username).execute()
    except Exception:
        pass


# ---------------------------------------------
# DICIONÁRIO DE IDIOMAS COMPLETOS
# ---------------------------------------------

TEXTOS = {
    "Português": {
        "login_title": "⚡ Acesso ao Meu Financeiro",
        "login_sub": "Entre com sua conta ou cadastre-se com seu nome completo.",
        "tab_login": "🔑 Entrar",
        "tab_register": "📝 Criar Conta",
        "user_label": "Usuário (E-mail ou Apelido)",
        "pass_label": "Senha",
        "btn_login_submit": "Entrar no Sistema",
        "login_success": "Bem-vindo de volta!",
        "login_error": "Usuário ou senha incorretos.",
        "reg_user_label": "Defina um Usuário de Login (ex: seu e-mail)",
        "reg_name_label": "Seu Nome Completo",
        "reg_pass_label": "Escolha uma Senha",
        "btn_reg_submit": "Cadastrar Nova Conta",
        "reg_warn": "Preencha todos os campos.",
        "reg_success": "Conta criada com sucesso! Vá na aba 'Entrar'.",
        "reg_error": "Este usuário já existe ou ocorreu uma falha no cadastro.",
        "nav_overview": "📊 Visão Geral & Gráficos",
        "nav_new": "➕ Novo Lançamento",
        "nav_manage": "✏️ Gerenciar & Editar",
        "nav_profile": "👤 Meu Perfil",
        "overview_title": "Visão Geral Financeira",
        "overview_sub": "Acompanhe seus fluxos, receitas e despesas por mês.",
        "no_data": "Nenhum lançamento cadastrado ainda. Vá em '➕ Novo Lançamento' para começar.",
        "total_rev": "💰 Receitas do Mês",
        "total_exp": "💸 Despesas do Mês",
        "balance": "⚡ Saldo do Mês",
        "pie_title": "📊 Despesas por Categoria",
        "bar_title": "📈 Evolução por Tipo",
        "recent_list": "📋 Lançamentos do Mês",
        "new_title": "➕ Novo Lançamento",
        "new_sub": "Adicione uma nova receita ou despesa detalhando o que foi gasto.",
        "date_label": "Data do Lançamento",
        "type_label": "Tipo",
        "value_label": "Valor",
        "cat_label": "Categoria Principal",
        "desc_label": "Descrição Específica",
        "save_btn": "🚀 Salvar Lançamento",
        "success_msg": "Lançamento salvo com sucesso!",
        "warn_desc": "Por favor, preencha a descrição.",
        "manage_title": "✏️ Gerenciar e Editar Lançamentos",
        "manage_sub": "Visualize, filtre ou exclua lançamentos antigos.",
        "del_btn": "🗑️ Excluir Selecionado",
        "profile_title": "👤 Meu Perfil de Usuário",
        "profile_sub": "Atualize suas informações cadastrais, senha ou foto de perfil.",
        "name_label": "Nome Completo",
        "address_label": "Endereço",
        "new_pass_label": "Nova Senha (deixe em branco para não alterar)",
        "photo_label": "Foto de Perfil",
        "remove_photo": "Remover foto atual",
        "save_profile": "Salvar Alterações",
        "profile_success": "Perfil atualizado com sucesso!",
        "profile_error": "Erro ao atualizar perfil.",
        "logout": "🚪 Sair da Conta",
        "context_pessoal": "Pessoal",
        "context_profissional": "Profissional / Comércio",
        "sidebar_pessoal": "🏠 Pessoal",
        "sidebar_profissional": "📊 Profissional / Comércio",
        "panel_mgmt": "💼 Painel de Gestão",
        "types": ["Despesa", "Receita"],
        "cat_pessoal": ["Aluguel", "Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Educação", "Salário", "Outros"],
        "cat_profissional": ["Vendas / Serviços", "Comissões", "Outras Receitas", "Fornecedores / Peças", "Operacional / Aluguel", "Impostos e Taxas", "Outras Despesas"]
    },
    "English": {
        "login_title": "⚡ My Finance Access",
        "login_sub": "Log in to your account or register.",
        "tab_login": "🔑 Log In",
        "tab_register": "📝 Register",
        "user_label": "Username (Email or Nickname)",
        "pass_label": "Password",
        "btn_login_submit": "Log In",
        "login_success": "Welcome back!",
        "login_error": "Incorrect username or password.",
        "reg_user_label": "Define a Login Username",
        "reg_name_label": "Your Full Name",
        "reg_pass_label": "Choose a Password",
        "btn_reg_submit": "Register New Account",
        "reg_warn": "Please fill in all fields.",
        "reg_success": "Account created successfully! Go to 'Log In'.",
        "reg_error": "This user already exists or registration failed.",
        "nav_overview": "📊 Overview & Charts",
        "nav_new": "➕ New Entry",
        "nav_manage": "✏️ Manage & Edit",
        "nav_profile": "👤 My Profile",
        "overview_title": "Financial Overview",
        "overview_sub": "Track your cash flows, income, and expenses by month.",
        "no_data": "No entries yet. Go to '➕ New Entry' to start.",
        "total_rev": "💰 Month Income",
        "total_exp": "💸 Month Expenses",
        "balance": "⚡ Month Balance",
        "pie_title": "📊 Expenses by Category",
        "bar_title": "📈 Trend by Type",
        "recent_list": "📋 Month Entries",
        "new_title": "➕ New Entry",
        "new_sub": "Add a new income or expense.",
        "date_label": "Entry Date",
        "type_label": "Type",
        "value_label": "Value",
        "cat_label": "Main Category",
        "desc_label": "Description",
        "save_btn": "🚀 Save Entry",
        "success_msg": "Entry saved successfully!",
        "warn_desc": "Please fill in the description.",
        "manage_title": "✏️ Manage and Edit Entries",
        "manage_sub": "View, filter, or delete old entries.",
        "del_btn": "🗑️ Delete Selected",
        "profile_title": "👤 User Profile",
        "profile_sub": "Update your profile info, password, or picture.",
        "name_label": "Full Name",
        "address_label": "Address",
        "new_pass_label": "New Password (leave blank to keep current)",
        "photo_label": "Profile Picture",
        "remove_photo": "Remove current picture",
        "save_profile": "Save Changes",
        "profile_success": "Profile updated successfully!",
        "profile_error": "Error updating profile.",
        "logout": "🚪 Log Out",
        "context_pessoal": "Personal",
        "context_profissional": "Professional / Business",
        "sidebar_pessoal": "🏠 Personal",
        "sidebar_profissional": "📊 Professional / Business",
        "panel_mgmt": "💼 Management Panel",
        "types": ["Expense", "Income"],
        "cat_pessoal": ["Rent", "Food", "Transport", "Housing", "Leisure", "Health", "Education", "Salary", "Others"],
        "cat_profissional": ["Sales / Services", "Commissions", "Other Income", "Suppliers / Parts", "Operational / Rent", "Taxes & Fees", "Other Expenses"]
    },
    "Français": {
        "login_title": "⚡ Accès à Mon Financier",
        "login_sub": "Connectez-vous ou créez un compte.",
        "tab_login": "🔑 Connexion",
        "tab_register": "📝 S'inscrire",
        "user_label": "Utilisateur (E-mail ou Pseudo)",
        "pass_label": "Mot de passe",
        "btn_login_submit": "Se connecter",
        "login_success": "Bienvenue !",
        "login_error": "Utilisateur ou mot de passe incorrect.",
        "reg_user_label": "Définir un nom d'utilisateur",
        "reg_name_label": "Votre Nom Complet",
        "reg_pass_label": "Choisir un mot de passe",
        "btn_reg_submit": "Créer le compte",
        "reg_warn": "Veuillez remplir tous les champs.",
        "reg_success": "Compte créé avec succès ! Allez dans l'onglet 'Connexion'.",
        "reg_error": "Cet utilisateur existe déjà ou une erreur est survenue.",
        "nav_overview": "📊 Vue d'ensemble",
        "nav_new": "➕ Nouvelle Entrée",
        "nav_manage": "✏️ Gérer & Éditer",
        "nav_profile": "👤 Mon Profil",
        "overview_title": "Vue d'ensemble financière",
        "overview_sub": "Suivez vos flux, revenus et dépenses par mois.",
        "no_data": "Aucune donnée pour l'instant. Allez dans '➕ Nouvelle Entrée'.",
        "total_rev": "💰 Revenus du Mois",
        "total_exp": "💸 Dépenses du Mois",
        "balance": "⚡ Solde du Mois",
        "pie_title": "📊 Dépenses par Catégorie",
        "bar_title": "📈 Évolution par Type",
        "recent_list": "📋 Entrées du Mois",
        "new_title": "➕ Nouvelle Entrée",
        "new_sub": "Ajoutez un revenu ou une dépense.",
        "date_label": "Date",
        "type_label": "Type",
        "value_label": "Valeur",
        "cat_label": "Catégorie Principale",
        "desc_label": "Description",
        "save_btn": "🚀 Enregistrer",
        "success_msg": "Enregistré avec succès !",
        "warn_desc": "Veuillez remplir la description.",
        "manage_title": "✏️ Gérer les Entrées",
        "manage_sub": "Visualisez ou supprimez vos entrées.",
        "del_btn": "🗑️ Supprimer la sélection",
        "profile_title": "👤 Mon Profil",
        "profile_sub": "Mettez à jour vos informations.",
        "name_label": "Nom Complet",
        "address_label": "Adresse",
        "new_pass_label": "Nouveau mot de passe (laisser vide pour ne pas changer)",
        "photo_label": "Photo de profil",
        "remove_photo": "Supprimer la photo actuelle",
        "save_profile": "Enregistrer les modifications",
        "profile_success": "Profil mis à jour avec succès !",
        "profile_error": "Erreur lors de la mise à jour.",
        "logout": "🚪 Se déconnecter",
        "context_pessoal": "Personnel",
        "context_profissional": "Professionnel / Commerce",
        "sidebar_pessoal": "🏠 Personnel",
        "sidebar_profissional": "📊 Professionnel / Commerce",
        "panel_mgmt": "💼 Panneau de Gestion",
        "types": ["Dépense", "Revenu"],
        "cat_pessoal": ["Loyer", "Alimentation", "Transport", "Logement", "Loisirs", "Santé", "Éducation", "Salaire", "Autres"],
        "cat_profissional": ["Ventes / Services", "Commissions", "Autres Revenus", "Fournisseurs / Pièces", "Général / Loyer", "Impôts", "Autres Dépenses"]
    },
    "Español": {
        "login_title": "⚡ Acceso a Mi Financiero",
        "login_sub": "Inicia sesión en tu cuenta o regístrate.",
        "tab_login": "🔑 Entrar",
        "tab_register": "📝 Registrarse",
        "user_label": "Usuario (Correo o Apodo)",
        "pass_label": "Contraseña",
        "btn_login_submit": "Iniciar Sesión",
        "login_success": "¡Bienvenido de nuevo!",
        "login_error": "Usuario o contraseña incorrectos.",
        "reg_user_label": "Define un nombre de usuario",
        "reg_name_label": "Tu Nombre Completo",
        "reg_pass_label": "Elige una Contraseña",
        "btn_reg_submit": "Crear Cuenta Nueva",
        "reg_warn": "Por favor llena todos los campos.",
        "reg_success": "¡Cuenta creada con éxito! Ve a la pestaña 'Entrar'.",
        "reg_error": "Este usuario ya existe o hubo un error.",
        "nav_overview": "📊 Visión General y Gráficos",
        "nav_new": "➕ Nuevo Movimiento",
        "nav_manage": "✏️ Gestionar y Editar",
        "nav_profile": "👤 Mi Perfil",
        "overview_title": "Resumen Financiero",
        "overview_sub": "Sigue tus ingresos y gastos por mes.",
        "no_data": "No hay registros todavía. Ve a '➕ Nuevo Movimiento'.",
        "total_rev": "💰 Ingresos del Mes",
        "total_exp": "💸 Gastos del Mes",
        "balance": "⚡ Saldo del Mes",
        "pie_title": "📊 Gastos por Categoría",
        "bar_title": "📈 Evolución por Tipo",
        "recent_list": "📋 Movimientos del Mes",
        "new_title": "➕ Nuevo Movimiento",
        "new_sub": "Agrega un ingreso o gasto.",
        "date_label": "Fecha del Movimiento",
        "type_label": "Tipo",
        "value_label": "Valor",
        "cat_label": "Categoría Principal",
        "desc_label": "Descripción",
        "save_btn": "🚀 Guardar Movimiento",
        "success_msg": "¡Movimiento guardado con éxito!",
        "warn_desc": "Por favor llena la descripción.",
        "manage_title": "✏️ Gestionar Movimientos",
        "manage_sub": "Visualiza, filtra o elimina registros antiguos.",
        "del_btn": "🗑️ Eliminar Seleccionado",
        "profile_title": "👤 Perfil de Usuario",
        "profile_sub": "Actualiza tu información, contraseña o foto.",
        "name_label": "Nombre Completo",
        "address_label": "Dirección",
        "new_pass_label": "Nueva Contraseña (dejar en blanco para no cambiar)",
        "photo_label": "Foto de Perfil",
        "remove_photo": "Eliminar foto actual",
        "save_profile": "Guardar Cambios",
        "profile_success": "¡Perfil actualizado con éxito!",
        "profile_error": "Error al actualizar perfil.",
        "logout": "🚪 Cerrar Sesión",
        "context_pessoal": "Personal",
        "context_profissional": "Profesional / Comercio",
        "sidebar_pessoal": "🏠 Personal",
        "sidebar_profissional": "📊 Profesional / Comercio",
        "panel_mgmt": "💼 Panel de Gestión",
        "types": ["Gasto", "Ingreso"],
        "cat_pessoal": ["Alquiler", "Alimentación", "Transporte", "Vivienda", "Ocio", "Salud", "Educación", "Salario", "Otros"],
        "cat_profissional": ["Ventas / Servicios", "Comisiones", "Otros Ingresos", "Proveedores / Piezas", "Operacional / Alquiler", "Impuestos", "Otros Gastos"]
    },
    "Italiano": {
        "login_title": "⚡ Accesso a Il Mio Finanziario",
        "login_sub": "Accedi al tuo account o registrati.",
        "tab_login": "🔑 Accedi",
        "tab_register": "📝 Registrati",
        "user_label": "Utente (Email o Nickname)",
        "pass_label": "Password",
        "btn_login_submit": "Accedi al Sistema",
        "login_success": "Bentornato!",
        "login_error": "Utente o password errati.",
        "reg_user_label": "Definisci un nome utente",
        "reg_name_label": "Il tuo Nome Completo",
        "reg_pass_label": "Scegli una Password",
        "btn_reg_submit": "Registra Nuovo Account",
        "reg_warn": "Compila tutti i campi.",
        "reg_success": "Account creato con successo! Vai su 'Accedi'.",
        "reg_error": "Utente già esistente o errore di registrazione.",
        "nav_overview": "📊 Panoramica & Grafici",
        "nav_new": "➕ Nuova Voce",
        "nav_manage": "✏️ Gestisci & Modifica",
        "nav_profile": "👤 Il Mio Profilo",
        "overview_title": "Panoramica Finanziaria",
        "overview_sub": "Monitora flussi, entrate e spese per mese.",
        "no_data": "Nessun inserimento. Vai su '➕ Nuova Voce' per iniziare.",
        "total_rev": "💰 Entrate del Mese",
        "total_exp": "💸 Spese del Mese",
        "balance": "⚡ Saldo del Mese",
        "pie_title": "📊 Spese per Categoria",
        "bar_title": "📈 Andamento per Tipo",
        "recent_list": "📋 Voci del Mese",
        "new_title": "➕ Nuova Voce",
        "new_sub": "Aggiungi un'entrata o una spesa.",
        "date_label": "Data",
        "type_label": "Tipo",
        "value_label": "Valore",
        "cat_label": "Categoria Principale",
        "desc_label": "Descrizione",
        "save_btn": "🚀 Salva Voce",
        "success_msg": "Salvato con successo!",
        "warn_desc": "Compila la descrizione.",
        "manage_title": "✏️ Gestisci Voci",
        "manage_sub": "Visualizza o elimina voci.",
        "del_btn": "🗑️ Elimina Selezionato",
        "profile_title": "👤 Profilo Utente",
        "profile_sub": "Aggiorna i tuoi dati.",
        "name_label": "Nome Completo",
        "address_label": "Indirizzo",
        "new_pass_label": "Nuova Password (lascia vuoto per non cambiare)",
        "photo_label": "Foto Profilo",
        "remove_photo": "Rimuovi foto attuale",
        "save_profile": "Salva Modifiche",
        "profile_success": "Profilo aggiornato!",
        "profile_error": "Errore durante l'aggiornamento.",
        "logout": "🚪 Disconnetti",
        "context_pessoal": "Personale",
        "context_profissional": "Professionale / Commerciale",
        "sidebar_pessoal": "🏠 Personale",
        "sidebar_profissional": "📊 Professionale / Commerciale",
        "panel_mgmt": "💼 Pannello di Gestione",
        "types": ["Spesa", "Entrata"],
        "cat_pessoal": ["Affitto", "Cibo", "Trasporto", "Alloggio", "Svago", "Salute", "Istruzione", "Stipendio", "Altro"],
        "cat_profissional": ["Vendite / Servizi", "Commissioni", "Altre Entrate", "Fornitori / Parti", "Operativo / Affitto", "Tasse", "Altre Spese"]
    },
    "Deutsch": {
        "login_title": "⚡ Mein Finanz-Zugang",
        "login_sub": "Melden Sie sich an oder registrieren Sie sich.",
        "tab_login": "🔑 Anmelden",
        "tab_register": "📝 Registrieren",
        "user_label": "Benutzername (E-Mail oder Nickname)",
        "pass_label": "Passwort",
        "btn_login_submit": "Anmelden",
        "login_success": "Willkommen zurück!",
        "login_error": "Falscher Benutzername oder Passwort.",
        "reg_user_label": "Benutzername festlegen",
        "reg_name_label": "Ihr Vollständiger Name",
        "reg_pass_label": "Passwort wählen",
        "btn_reg_submit": "Konto erstellen",
        "reg_warn": "Bitte füllen Sie alle Felder aus.",
        "reg_success": "Konto erfolgreich erstellt! Gehen Sie zu 'Anmelden'.",
        "reg_error": "Benutzer existiert bereits oder Fehler.",
        "nav_overview": "📊 Übersicht & Diagramme",
        "nav_new": "➕ Neuer Eintrag",
        "nav_manage": "✏️ Verwalten & Bearbeiten",
        "nav_profile": "👤 Mein Profil",
        "overview_title": "Finanzübersicht",
        "overview_sub": "Verfolgen Sie Einnahmen und Ausgaben nach Monat.",
        "no_data": "Noch keine Einträge. Gehen Sie zu '➕ Neuer Eintrag'.",
        "total_rev": "💰 Einnahmen des Monats",
        "total_exp": "💸 Ausgaben des Monats",
        "balance": "⚡ Saldo des Monats",
        "pie_title": "📊 Ausgaben nach Kategorie",
        "bar_title": "📈 Trend nach Typ",
        "recent_list": "📋 Einträge des Monats",
        "new_title": "➕ Neuer Eintrag",
        "new_sub": "Fügen Sie eine Einnahme oder Ausgabe hinzu.",
        "date_label": "Datum",
        "type_label": "Typ",
        "value_label": "Wert",
        "cat_label": "Hauptkategorie",
        "desc_label": "Beschreibung",
        "save_btn": "🚀 Eintrag Speichern",
        "success_msg": "Erfolgreich gespeichert!",
        "warn_desc": "Bitte Beschreibung ausfüllen.",
        "manage_title": "✏️ Einträge Verwalten",
        "manage_sub": "Einträge anzeigen oder löschen.",
        "del_btn": "🗑️ Ausgewählte Löschen",
        "profile_title": "👤 Benutzerprofil",
        "profile_sub": "Aktualisieren Sie Ihre Daten.",
        "name_label": "Vollständiger Name",
        "address_label": "Adresse",
        "new_pass_label": "Neues Passwort (leer lassen für keine Änderung)",
        "photo_label": "Profilbild",
        "remove_photo": "Aktuelles Bild entfernen",
        "save_profile": "Änderungen Speichern",
        "profile_success": "Profil erfolgreich aktualisiert!",
        "profile_error": "Fehler beim Aktualisieren.",
        "logout": "🚪 Abmelden",
        "context_pessoal": "Persönlich",
        "context_profissional": "Beruflich / Gewerbe",
        "sidebar_pessoal": "🏠 Persönlich",
        "sidebar_profissional": "📊 Beruflich / Gewerbe",
        "panel_mgmt": "💼 Verwaltungsbereich",
        "types": ["Ausgabe", "Einnahme"],
        "cat_pessoal": ["Miete", "Essen", "Transport", "Wohnen", "Freizeit", "Gesundheit", "Bildung", "Gehalt", "Andere"],
        "cat_profissional": ["Verkäufe / Dienste", "Provisionen", "Sonstige Einnahmen", "Lieferanten / Teile", "Betrieb / Miete", "Steuern", "Sonstige Ausgaben"]
    }
}

MOEDAS = {
    "Real (R$)": "R$",
    "Euro (€)": "€",
    "Dólar ($)": "$"
}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'idioma' not in st.session_state:
    st.session_state['idioma'] = "Português"
if 'moeda' not in st.session_state:
    st.session_state['moeda'] = "Real (R$)"

lista_idiomas = list(TEXTOS.keys())

if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h2 style='text-align: center;'>{TEXTOS[st.session_state['idioma']]['login_title']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>{TEXTOS[st.session_state['idioma']]['login_sub']}</p>", unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs([TEXTOS[st.session_state['idioma']]['tab_login'], TEXTOS[st.session_state['idioma']]['tab_register']])
        
        with tab_login:
            with st.form("form_login"):
                u_input = st.text_input(TEXTOS[st.session_state['idioma']]['user_label'])
                p_input = st.text_input(TEXTOS[st.session_state['idioma']]['pass_label'], type="password")
                submit_login = st.form_submit_button(TEXTOS[st.session_state['idioma']]['btn_login_submit'], use_container_width=True)
                
                if submit_login:
                    ok, err = autenticar_usuario(u_input, p_input)
                    if ok:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u_input
                        st.success(TEXTOS[st.session_state['idioma']]['login_success'])
                        st.rerun()
                    else:
                        if err:
                            st.error(f"{TEXTOS[st.session_state['idioma']]['login_error']} (Detalhe: {err})")
                        else:
                            st.error(TEXTOS[st.session_state['idioma']]['login_error'])
                        
        with tab_reg:
            with st.form("form_reg"):
                reg_user = st.text_input(TEXTOS[st.session_state['idioma']]['reg_user_label'])
                reg_name = st.text_input(TEXTOS[st.session_state['idioma']]['reg_name_label'])
                reg_pass = st.text_input(TEXTOS[st.session_state['idioma']]['reg_pass_label'], type="password")
                submit_reg = st.form_submit_button(TEXTOS[st.session_state['idioma']]['btn_reg_submit'], use_container_width=True)
                
                if submit_reg:
                    if reg_user and reg_name and reg_pass:
                        sucesso, err_msg = cadastrar_usuario(reg_user, reg_name, reg_pass)
                        if sucesso:
                            st.success(TEXTOS[st.session_state['idioma']]['reg_success'])
                        else:
                            st.error(f"{TEXTOS[st.session_state['idioma']]['reg_error']} ({err_msg})")
                    else:
                        st.warning(TEXTOS[st.session_state['idioma']]['reg_warn'])

        st.markdown("<hr>", unsafe_allow_html=True)
        sel_lang = st.selectbox("🌐 Idioma / Language", lista_idiomas, index=lista_idiomas.index(st.session_state['idioma']), key="login_lang_sel")
        if sel_lang != st.session_state['idioma']:
            st.session_state['idioma'] = sel_lang
            st.rerun()

        sel_moeda = st.selectbox("💶 Moeda / Currency", list(MOEDAS.keys()), index=list(MOEDAS.keys()).index(st.session_state['moeda']), key="login_moeda_sel")
        if sel_moeda != st.session_state['moeda']:
            st.session_state['moeda'] = sel_moeda
            st.rerun()

else:
    dados_user = obter_dados_usuario(st.session_state['username'])
    nome_completo_user = dados_user[0] if dados_user and dados_user[0] else st.session_state['username']
    foto_blob_user = dados_user[2] if dados_user and len(dados_user) > 2 else None

    simbolo_moeda = MOEDAS[st.session_state['moeda']]
    t = TEXTOS[st.session_state['idioma']]

    with st.sidebar:
        if foto_blob_user:
            try:
                img = Image.open(io.BytesIO(foto_blob_user))
                st.image(img, width=100)
            except Exception:
                st.write("📷")
        else:
            st.write("👤")

        st.markdown(f"### ⚡ Olá, {nome_completo_user}")
        st.markdown("---")

        contexto_atual = st.radio(
            t["panel_mgmt"],
            [t["sidebar_pessoal"], t["sidebar_profissional"]],
            key="sidebar_context_radio",
        )
        contexto_limpo = "Profissional" if "Profissional" in contexto_atual or "Business" in contexto_atual or "Commerce" in contexto_atual or "Gewerbe" in contexto_atual else "Pessoal"

        st.markdown("---")

        sel_lang = st.selectbox("🌐 Idioma / Language", lista_idiomas, index=lista_idiomas.index(st.session_state['idioma']), key="side_lang_sel")
        if sel_lang != st.session_state['idioma']:
            st.session_state['idioma'] = sel_lang
            st.rerun()

        sel_moeda = st.selectbox("💶 Moeda / Currency", list(MOEDAS.keys()), index=list(MOEDAS.keys()).index(st.session_state['moeda']), key="side_moeda_sel")
        if sel_moeda != st.session_state['moeda']:
            st.session_state['moeda'] = sel_moeda
            st.rerun()

        st.markdown("---")
        menu = st.radio("Navegação", [
            t['nav_overview'],
            t['nav_new'],
            t['nav_manage'],
            t['nav_profile']
        ], key="side_menu_radio")

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button(t['logout'], use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.rerun()

    df_total = carregar_dados(st.session_state['username'])
    if not df_total.empty and "contexto" in df_total.columns:
        df = df_total[df_total["contexto"] == contexto_limpo].copy()
    else:
        df = pd.DataFrame()

    nome_contexto_traduzido = t["context_profissional"] if contexto_limpo == "Profissional" else t["context_pessoal"]

    if menu == t['nav_overview']:
        st.title(f"{t['overview_title']} ({nome_contexto_traduzido})")
        st.write(t['overview_sub'])

        if df.empty:
            st.info(t['no_data'])
        else:
            df["data"] = pd.to_datetime(df["data"])
            df["mes_ano"] = df["data"].dt.strftime("%Y-%m")
            
            meses_disponiveis = sorted(df["mes_ano"].unique(), reverse=True)
            mes_selecionado = st.selectbox("📅 Selecione o Mês", meses_disponiveis)
            
            df_mes = df[df["mes_ano"] == mes_selecionado]

            total_receitas = df_mes[df_mes['tipo'] == t['types'][1]]['valor'].sum() if not df_mes.empty else 0.0
            total_despesas = df_mes[df_mes['tipo'] == t['types'][0]]['valor'].sum() if not df_mes.empty else 0.0
            saldo = total_receitas - total_despesas

            col1, col2, col3 = st.columns(3)
            col1.metric(t['total_rev'], f"{simbolo_moeda} {total_receitas:,.2f}")
            col2.metric(t['total_exp'], f"{simbolo_moeda} {total_despesas:,.2f}")
            col3.metric(t['balance'], f"{simbolo_moeda} {saldo:,.2f}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                df_desp = df_mes[df_mes['tipo'] == t['types'][0]] if not df_mes.empty else pd.DataFrame()
                if not df_desp.empty:
                    fig_pie = px.pie(df_desp, names='categoria', values='valor', title=t['pie_title'], hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem despesas para exibir no gráfico neste mês.")

            with c2:
                if not df_mes.empty:
                    fig_bar = px.bar(df_mes, x='data', y='valor', color='tipo', title=t['bar_title'], barmode='group')
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sem dados para o gráfico.")

            st.subheader(t['recent_list'])
            st.dataframe(df_mes, use_container_width=True)

    elif menu == t['nav_new']:
        st.title(f"{t['new_title']} ({nome_contexto_traduzido})")
        st.write(t['new_sub'])

        with st.form("form_novo_lancamento"):
            data_lanc = st.date_input(t['date_label'], datetime.date.today())
            tipo_lanc = st.selectbox(t['type_label'], t['types'])
            valor_lanc = st.number_input(f"{t['value_label']} ({simbolo_moeda})", min_value=0.0, format="%.2f")
            
            lista_cat_atual = t['cat_profissional'] if contexto_limpo == "Profissional" else t['cat_pessoal']
            cat_lanc = st.selectbox(t['cat_label'], lista_cat_atual)
            desc_lanc = st.text_input(t['desc_label'])
            
            submit_lanc = st.form_submit_button(t['save_btn'], use_container_width=True)
            if submit_lanc:
                if valor_lanc > 0:
                    sucesso = salvar_lancamento(
                        st.session_state['username'],
                        str(data_lanc),
                        desc_lanc,
                        cat_lanc,
                        tipo_lanc,
                        valor_lanc,
                        contexto_limpo
                    )
                    if sucesso:
                        st.success(t['success_msg'])
                        st.rerun()
                    else:
                        st.error("Erro ao salvar no Supabase.")
                else:
                    st.warning("Por favor, informe um valor maior que zero.")

    elif menu == t['nav_manage']:
        st.title(f"{t['manage_title']} ({nome_contexto_traduzido})")
        st.write(t['manage_sub'])

        if df.empty:
            st.info(t['no_data'])
        else:
            st.dataframe(df, use_container_width=True)
            id_del = st.selectbox("ID do lançamento para excluir", df['id'].tolist())
            if st.button(t['del_btn']):
                deletar_lancamento(id_del, st.session_state['username'])
                st.success("Lançamento excluído com sucesso!")
                st.rerun()

    elif menu == t['nav_profile']:
        st.title(t['profile_title'])
        st.write(t['profile_sub'])

        dados_atuais = obter_dados_usuario(st.session_state['username'])
        nome_atual = dados_atuais[0] if dados_atuais and dados_atuais[0] else ""
        end_atual = dados_atuais[1] if dados_atuais and dados_atuais[1] else ""

        with st.form("form_perfil"):
            novo_nome = st.text_input(t['name_label'], value=nome_atual)
            novo_endereco = st.text_input(t['address_label'], value=end_atual)
            nova_senha = st.text_input(t['new_pass_label'], type="password")
            
            foto_upload = st.file_uploader(t['photo_label'], type=["png", "jpg", "jpeg"])
            remover_foto_check = st.checkbox(t['remove_photo'])

            submit_perfil = st.form_submit_button(t['save_profile'], use_container_width=True)

            if submit_perfil:
                foto_blob = None
                if foto_upload is not None:
                    foto_blob = foto_upload.read()
                
                sucesso_p, err_p = atualizar_perfil(st.session_state['username'], novo_nome, novo_endereco, nova_senha, foto_blob, remover_foto_check)
                if sucesso_p:
                    st.success(t['profile_success'])
                    st.rerun()
                else:
                    st.error(f"{t['profile_error']} ({err_p})")
