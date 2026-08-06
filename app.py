import datetime
import hashlib
import io
import pandas as pd
from PIL import Image
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Controle Financeiro | Multi-Usuário",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <head>
        <meta property="og:title" content="Controle Financeiro | Multi-Usuário">
        <meta property="og:description" content="Sistema de gestão financeira online, simples, rápido e seguro.">
        <meta property="og:image" content="https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?q=80&w=1200&auto=format&fit=crop">
        <link rel="apple-touch-icon" href="https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=512&auto=format&fit=crop">
    </head>
""",
    unsafe_allow_html=True,
)


def make_hash(password):
  return hashlib.sha256(str.encode(password)).hexdigest()


def check_hash(password, hashed_text):
  if make_hash(password) == hashed_text:
    return True
  return False


def init_db():
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            nome_completo TEXT,
            senha TEXT
        )
    """)
  for col, col_type in [("endereco", "TEXT"), ("foto_perfil", "BLOB")]:
    try:
      cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {col_type}")
    except:
      pass

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            data TEXT,
            descricao TEXT,
            categoria TEXT,
            tipo TEXT,
            valor REAL
        )
    """)
  try:
    cursor.execute("ALTER TABLE lancamentos ADD COLUMN username TEXT")
  except:
    pass

  try:
    cursor.execute(
        "ALTER TABLE lancamentos ADD COLUMN contexto TEXT DEFAULT 'Pessoal'"
    )
  except:
    pass

  conn.commit()
  conn.close()


init_db()


def cadastrar_usuario(username, nome_completo, senha):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  try:
    cursor.execute(
        "INSERT INTO usuarios (username, nome_completo, senha) VALUES (?, ?, ?)",
        (username, nome_completo, make_hash(senha)),
    )
    conn.commit()
    conn.close()
    return True
  except:
    conn.close()
    return False


def autenticar_usuario(username, senha):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  cursor.execute("SELECT senha FROM usuarios WHERE username = ?", (username,))
  result = cursor.fetchone()
  conn.close()
  if result:
    return check_hash(senha, result[0])
  return False


def obter_dados_usuario(username):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT nome_completo, endereco, foto_perfil FROM usuarios WHERE"
      " username = ?",
      (username,),
  )
  result = cursor.fetchone()
  conn.close()
  return result


def atualizar_perfil(
    username,
    novo_nome,
    novo_endereco,
    nova_senha,
    nova_foto_blob,
    remover_foto=False,
):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  try:
    if remover_foto:
      foto_sql = None
    else:
      foto_sql = nova_foto_blob

    if nova_senha:
      hash_senha = make_hash(nova_senha)
      if remover_foto:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ?,"
            " foto_perfil = NULL WHERE username = ?",
            (novo_nome, novo_endereco, hash_senha, username),
        )
      elif nova_foto_blob is not None:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ?,"
            " foto_perfil = ? WHERE username = ?",
            (novo_nome, novo_endereco, hash_senha, nova_foto_blob, username),
        )
      else:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ? WHERE"
            " username = ?",
            (novo_nome, novo_endereco, hash_senha, username),
        )
    else:
      if remover_foto:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ?, foto_perfil ="
            " NULL WHERE username = ?",
            (novo_nome, novo_endereco, username),
        )
      elif nova_foto_blob is not None:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ?, foto_perfil ="
            " ? WHERE username = ?",
            (novo_nome, novo_endereco, nova_foto_blob, username),
        )
      else:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = ?, endereco = ? WHERE"
            " username = ?",
            (novo_nome, novo_endereco, username),
        )
    conn.commit()
    conn.close()
    return True
  except:
    conn.close()
    return False


def carregar_dados(username):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  df = pd.read_sql_query(
      "SELECT * FROM lancamentos WHERE username = ?", conn, params=(username,)
  )
  conn.close()
  if "contexto" not in df.columns:
    df["contexto"] = "Pessoal"
  return df


def salvar_lancamento(
    username, data, descricao, categoria, tipo, valor, contexto
):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO lancamentos (username, data, descricao, categoria, tipo,"
      " valor, contexto) VALUES (?, ?, ?, ?, ?, ?, ?)",
      (username, data, descricao, categoria, tipo, valor, contexto),
  )
  conn.commit()
  conn.close()


def deletar_lancamento(id_lancamento, username):
  import sqlite3

  conn = sqlite3.connect("financeiro.db")
  cursor = conn.cursor()
  cursor.execute(
      "DELETE FROM lancamentos WHERE id = ? AND username = ?",
      (id_lancamento, username),
  )
  conn.commit()
  conn.close()


TEXTOS = {
    "Português": {
        "login_title": "Acesso ao Controle Financeiro",
        "login_sub": (
            "Entre com sua conta ou cadastre-se com seu nome completo."
        ),
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
        "reg_error": (
            "Este usuário já existe ou ocorreu uma falha no cadastro."
        ),
        "nav_overview": "📊 Visão Geral & Gráficos",
        "nav_new": "➕ Novo Lançamento",
        "nav_manage": "✏️ Gerenciar & Editar",
        "nav_profile": "👤 Meu Perfil",
        "overview_title": "Controle Financeiro",
        "overview_sub": (
            "Acompanhe suas entradas, saídas e resultados consolidados."
        ),
        "no_data": (
            "Nenhum lançamento no painel {contexto} ainda. Vá em '➕"
            " {nav_novo}' para começar."
        ),
        "total_rev": "📥 Entradas / Receitas",
        "total_exp": "📉 Saídas / Despesas",
        "invest_month": "📈 Investimentos / Aportes",
        "invest_accumulated": "💎 Total Acumulado em Investimentos",
        "account_balance": "💰 Saldo do Período",
        "accumulated_balance": "🏦 Saldo Acumulado Total",
        "pie_title": "📊 Despesas por Categoria",
        "bar_title": "📈 Evolução Diária / Mensal",
        "recent_list": "📋 Lançamentos do Período",
        "new_title": "➕ Novo Lançamento",
        "new_sub": (
            "Adicione uma nova entrada, saída ou investimento de forma rápida."
        ),
        "date_label": "Data do Lançamento",
        "type_label": "Tipo de Movimentação",
        "value_label": "Valor",
        "cat_label": "Categoria",
        "desc_label": "Descrição / Observação (Opcional)",
        "save_btn": "🚀 Salvar Lançamento",
        "success_msg": "Lançamento salvo com sucesso!",
        "warn_val": "Por favor, informe um valor maior que zero.",
        "manage_title": "✏️ Gerenciar e Editar Lançamentos",
        "manage_sub": "Visualize, filtre ou exclua lançamentos antigos.",
        "del_btn": "🗑️ Excluir Selecionado",
        "profile_title": "👤 Meu Perfil de Usuário",
        "profile_sub": (
            "Atualize suas informações cadastrais, senha ou foto de perfil."
        ),
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
        "nav_novo_label": "Novo Lançamento",
        "types": ["Despesa", "Receita", "Investimento"],
        "cat_pessoal": [
            "Aluguel",
            "Alimentação",
            "Transporte",
            "Moradia",
            "Lazer",
            "Saúde",
            "Educação",
            "Salário Pessoal",
            "Investimentos",
            "Outros",
        ],
        "cat_profissional": [
            "Faturamento de Vendas / Atendimentos",
            "Prestação de Serviços / Comissões",
            "Outras Receitas",
            "Compra de Mercadorias / Insumos / Peças",
            "Fornecedores e Parcerias",
            "Operacional / Aluguel / Contas",
            "Ferramentas e Equipamentos",
            "Impostos, Taxas e Encargos",
            "Investimento Comercial",
            "Outras Despesas",
        ],
    },
    "English": {
        "login_title": "Financial Control Access",
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
        "overview_title": "Financial Control",
        "overview_sub": "Track your cash flows, income, and expenses.",
        "no_data": (
            "No entries in the {context} panel yet. Go to '➕ {nav_novo}' to"
            " start."
        ),
        "total_rev": "📥 Income / Inflows",
        "total_exp": "📉 Expenses / Outflows",
        "invest_month": "📈 Investments",
        "invest_accumulated": "💎 Total Accumulated Investments",
        "account_balance": "💰 Period Balance",
        "accumulated_balance": "🏦 Total Accumulated Balance",
        "pie_title": "📊 Expenses by Category",
        "bar_title": "📈 Trend by Type",
        "recent_list": "📋 Entries",
        "new_title": "➕ New Entry",
        "new_sub": "Add a new income, expense, or investment.",
        "date_label": "Entry Date",
        "type_label": "Type",
        "value_label": "Value",
        "cat_label": "Category",
        "desc_label": "Description (Optional)",
        "save_btn": "🚀 Save Entry",
        "success_msg": "Entry saved successfully!",
        "warn_val": "Please enter a value greater than zero.",
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
        "nav_novo_label": "New Entry",
        "types": ["Expense", "Income", "Investment"],
        "cat_pessoal": [
            "Rent",
            "Food",
            "Transport",
            "Housing",
            "Leisure",
            "Health",
            "Education",
            "Personal Salary",
            "Investments",
            "Others",
        ],
        "cat_profissional": [
            "Sales Revenue / Services",
            "Commissions / Freelance",
            "Other Income",
            "Goods / Supplies / Parts Purchase",
            "Suppliers & Partnerships",
            "Operational / Rent / Utilities",
            "Tools & Equipment",
            "Taxes & Fees",
            "Commercial Investment",
            "Other Expenses",
        ],
    },
    "Français": {
        "login_title": "Accès au Contrôle Financier",
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
        "reg_success": (
            "Compte créé avec succès ! Allez dans l'onglet 'Connexion'."
        ),
        "reg_error": "Cet utilisateur existe déjà ou une erreur est survenue.",
        "nav_overview": "📊 Vue d'ensemble",
        "nav_new": "➕ Nouvelle Entrée",
        "nav_manage": "✏️ Gérer & Éditer",
        "nav_profile": "👤 Mon Profil",
        "overview_title": "Contrôle Financier",
        "overview_sub": "Suivez vos flux et revenus.",
        "no_data": (
            "Aucune donnée dans le panneau {context} pour l'instant. Allez dans"
            " '➕ {nav_novo}'."
        ),
        "total_rev": "📥 Entrées",
        "total_exp": "📉 Sorties",
        "invest_month": "📈 Investissements",
        "invest_accumulated": "💎 Total Cumulé des Investissements",
        "account_balance": "💰 Solde de la Période",
        "accumulated_balance": "🏦 Solde cumulé total",
        "pie_title": "📊 Dépenses par Catégorie",
        "bar_title": "📈 Évolution",
        "recent_list": "📋 Entrées",
        "new_title": "➕ Nouvelle Entrée",
        "new_sub": "Ajoutez un mouvement.",
        "date_label": "Date",
        "type_label": "Type",
        "value_label": "Valeur",
        "cat_label": "Catégorie",
        "desc_label": "Description (Optionnel)",
        "save_btn": "🚀 Enregistrer",
        "success_msg": "Enregistré avec succès !",
        "warn_val": "Veuillez entrer une valeur supérieure à zéro.",
        "manage_title": "✏️ Gérer les Entrées",
        "manage_sub": "Visualisez ou supprimez vos entrées.",
        "del_btn": "🗑️ Supprimer la sélection",
        "profile_title": "👤 Mon Profil",
        "profile_sub": "Mettez à jour vos informations.",
        "name_label": "Nom Complet",
        "address_label": "Adresse",
        "new_pass_label": (
            "Nouveau mot de passe (laisser vide pour ne pas changer)"
        ),
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
        "nav_novo_label": "Nouvelle Entrée",
        "types": ["Dépense", "Revenu", "Investissement"],
        "cat_pessoal": [
            "Loyer",
            "Alimentation",
            "Transport",
            "Logement",
            "Loisirs",
            "Santé",
            "Éducation",
            "Salaire Personnel",
            "Investissements",
            "Autres",
        ],
        "cat_profissional": [
            "Chiffre d'affaires / Ventes",
            "Prestation de services / Commissions",
            "Autres Revenus",
            "Achat de marchandises / Fournitures / Pièces",
            "Fournisseurs et Partenariats",
            "Frais généraux / Loyer / Charges",
            "Outils et Équipements",
            "Impôts et Taxes",
            "Investissement Commercial",
            "Autres Dépenses",
        ],
    },
    "Español": {
        "login_title": "Acceso al Control Financiero",
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
        "overview_title": "Control Financiero",
        "overview_sub": "Sigue tus ingresos y gastos.",
        "no_data": (
            "No hay registros en el panel {context} todavía. Ve a '➕ {nav_novo}'."
        ),
        "total_rev": "📥 Entradas",
        "total_exp": "📉 Salidas",
        "invest_month": "📈 Inversiones",
        "invest_accumulated": "💎 Total Acumulado en Inversiones",
        "account_balance": "💰 Saldo del Periodo",
        "accumulated_balance": "🏦 Saldo Acumulado Total",
        "pie_title": "📊 Gastos por Categoría",
        "bar_title": "📈 Evolución",
        "recent_list": "📋 Movimientos",
        "new_title": "➕ Nuevo Movimiento",
        "new_sub": "Agrega un movimiento.",
        "date_label": "Fecha del Movimiento",
        "type_label": "Tipo",
        "value_label": "Valor",
        "cat_label": "Categoría",
        "desc_label": "Descripción (Opcional)",
        "save_btn": "🚀 Guardar Movimiento",
        "success_msg": "¡Movimiento guardado con éxito!",
        "warn_val": "Por favor ingrese un valor mayor que cero.",
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
        "nav_novo_label": "Nuevo Movimiento",
        "types": ["Gasto", "Ingreso", "Inversión"],
        "cat_pessoal": [
            "Alquiler",
            "Alimentación",
            "Transporte",
            "Vivienda",
            "Ocio",
            "Salud",
            "Educación",
            "Salario Personal",
            "Inversiones",
            "Otros",
        ],
        "cat_profissional": [
            "Facturación de Ventas / Servicios",
            "Prestación de Servicios / Comisiones",
            "Otros Ingresos",
            "Compra de Mercancías / Insumos / Piezas",
            "Proveedores y Alianzas",
            "Operacional / Alquiler / Cuentas",
            "Herramientas y Equipos",
            "Impuestos y Tasas",
            "Inversión Comercial",
            "Otros Gastos",
        ],
    },
    "Italiano": {
        "login_title": "Accesso al Controllo Finanziario",
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
        "overview_title": "Controllo Finanziario",
        "overview_sub": "Monitora flussi ed entrate.",
        "no_data": (
            "Nessun inserimento nel pannello {context}. Vai su '➕ {nav_novo}'"
            " per iniziare."
        ),
        "total_rev": "📥 Entrate",
        "total_exp": "📉 Uscite",
        "invest_month": "📈 Investimenti",
        "invest_accumulated": "💎 Totale Accumulato in Investimenti",
        "account_balance": "💰 Saldo del Periodo",
        "accumulated_balance": "🏦 Saldo Accumulato Totale",
        "pie_title": "📊 Spese per Categoria",
        "bar_title": "📈 Andamento",
        "recent_list": "📋 Voci",
        "new_title": "➕ Nuova Voce",
        "new_sub": "Aggiungi una voce.",
        "date_label": "Data",
        "type_label": "Tipo",
        "value_label": "Valore",
        "cat_label": "Categoria",
        "desc_label": "Descrizione (Opzionale)",
        "save_btn": "🚀 Salva Voce",
        "success_msg": "Salvato con successo!",
        "warn_val": "Inserisci un valore maggiore di zero.",
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
        "nav_novo_label": "Nuova Voce",
        "types": ["Spesa", "Entrata", "Investimento"],
        "cat_pessoal": [
            "Affitto",
            "Cibo",
            "Trasporto",
            "Alloggio",
            "Svago",
            "Salute",
            "Istruzione",
            "Stipendio Personale",
            "Investimenti",
            "Altro",
        ],
        "cat_profissional": [
            "Fatturato Vendite / Servizi",
            "Prestazione di Servizi / Commissioni",
            "Altre Entrate",
            "Acquisto Merci / Forniture / Parti",
            "Fornitori e Partnership",
            "Spese Generali / Affitto / Utenze",
            "Utensili e Attrezzature",
            "Tasse e Commissioni",
            "Investimento Commerciale",
            "Altre Spese",
        ],
    },
    "Deutsch": {
        "login_title": "Finanzkontrolle Zugang",
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
        "overview_title": "Finanzkontrolle",
        "overview_sub": "Verfolgen Sie Einnahmen und Ausgaben.",
        "no_data": (
            "Noch keine Einträge im Bereich {context}. Gehen Sie zu '➕"
            " {nav_novo}'."
        ),
        "total_rev": "📥 Einnahmen",
        "total_exp": "📉 Ausgaben",
        "invest_month": "📈 Investitionen",
        "invest_accumulated": "💎 Gesamte Akkumulierte Investitionen",
        "account_balance": "💰 Saldo",
        "accumulated_balance": "🏦 Akkumulierter Saldo",
        "pie_title": "📊 Ausgaben nach Kategorie",
        "bar_title": "📈 Trend",
        "recent_list": "📋 Einträge",
        "new_title": "➕ Neuer Eintrag",
        "new_sub": "Fügen Sie einen Eintrag hinzu.",
        "date_label": "Datum",
        "type_label": "Typ",
        "value_label": "Wert",
        "cat_label": "Kategorie",
        "desc_label": "Beschreibung (Optional)",
        "save_btn": "🚀 Eintrag Speichern",
        "success_msg": "Erfolgreich gespeichert!",
        "warn_val": "Bitte geben Sie einen Wert größer als Null ein.",
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
        "nav_novo_label": "Neuer Eintrag",
        "types": ["Ausgabe", "Einnahme", "Investition"],
        "cat_pessoal": [
            "Miete",
            "Essen",
            "Transport",
            "Wohnen",
            "Freizeit",
            "Gesundheit",
            "Bildung",
            "Persönliches Gehalt",
            "Investitionen",
            "Andere",
        ],
        "cat_profissional": [
            "Umsatz / Verkäufe",
            "Dienstleistungen / Provisionen",
            "Sonstige Einnahmen",
            "Wareneinkauf / Verbrauchsmaterial / Teile",
            "Lieferanten & Partnerschaften",
            "Betriebskosten / Miete / Nebenkosten",
            "Werkzeuge & Ausrüstung",
            "Steuern & Gebühren",
            "Gewerbliche Investition",
            "Sonstige Ausgaben",
        ],
    },
}

MOEDAS = {"Real (R$)": "R$", "Euro (€)": "€", "Dólar ($)": "$"}

if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False
if "username" not in st.session_state:
  st.session_state["username"] = ""
if "idioma" not in st.session_state:
  st.session_state["idioma"] = "Português"
if "moeda" not in st.session_state:
  st.session_state["moeda"] = "Real (R$)"

lista_idiomas = list(TEXTOS.keys())

if not st.session_state["logged_in"]:
  st.markdown("<br><br>", unsafe_allow_html=True)
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.markdown(
        f"<h2 style='text-align:"
        f" center;'>{TEXTOS[st.session_state['idioma']]['login_title']}</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='text-align: center;"
        f" color: gray;'>{TEXTOS[st.session_state['idioma']]['login_sub']}</p>",
        unsafe_allow_html=True,
    )

    tab_login, tab_reg = st.tabs([
        TEXTOS[st.session_state["idioma"]]["tab_login"],
        TEXTOS[st.session_state["idioma"]]["tab_register"],
    ])

    with tab_login:
      with st.form("form_login"):
        u_input = st.text_input(
            TEXTOS[st.session_state["idioma"]]["user_label"]
        )
        p_input = st.text_input(
            TEXTOS[st.session_state["idioma"]]["pass_label"], type="password"
        )
        submit_login = st.form_submit_button(
            TEXTOS[st.session_state["idioma"]]["btn_login_submit"],
            use_container_width=True,
        )

        if submit_login:
          if autenticar_usuario(u_input, p_input):
            st.session_state["logged_in"] = True
            st.session_state["username"] = u_input
            st.success(TEXTOS[st.session_state["idioma"]]["login_success"])
            st.rerun()
          else:
            st.error(TEXTOS[st.session_state["idioma"]]["login_error"])

    with tab_reg:
      with st.form("form_reg"):
        reg_user = st.text_input(
            TEXTOS[st.session_state["idioma"]]["reg_user_label"]
        )
        reg_name = st.text_input(
            TEXTOS[st.session_state["idioma"]]["reg_name_label"]
        )
        reg_pass = st.text_input(
            TEXTOS[st.session_state["idioma"]]["reg_pass_label"], type="password"
        )
        submit_reg = st.form_submit_button(
            TEXTOS[st.session_state["idioma"]]["btn_reg_submit"],
            use_container_width=True,
        )

        if submit_reg:
          if reg_user and reg_name and reg_pass:
            if cadastrar_usuario(reg_user, reg_name, reg_pass):
              st.success(TEXTOS[st.session_state["idioma"]]["reg_success"])
            else:
              st.error(TEXTOS[st.session_state["idioma"]]["reg_error"])
          else:
            st.warning(TEXTOS[st.session_state["idioma"]]["reg_warn"])

    st.markdown("<hr>", unsafe_allow_html=True)
    sel_lang = st.selectbox(
        "🌐 Idioma / Language",
        lista_idiomas,
        index=lista_idiomas.index(st.session_state["idioma"]),
    )
    if sel_lang != st.session_state["idioma"]:
      st.session_state["idioma"] = sel_lang
      st.rerun()

    sel_moeda = st.selectbox(
        "💶 Moeda / Currency",
        list(MOEDAS.keys()),
        index=list(MOEDAS.keys()).index(st.session_state["moeda"]),
    )
    if sel_moeda != st.session_state["moeda"]:
      st.session_state["moeda"] = sel_moeda
      st.rerun()

else:
  dados_user = obter_dados_usuario(st.session_state["username"])
  nome_completo_user = (
      dados_user[0]
      if dados_user and dados_user[0]
      else st.session_state["username"]
  )
  foto_blob_user = dados_user[2] if dados_user and len(dados_user) > 2 else None

  simbolo_moeda = MOEDAS[st.session_state["moeda"]]
  t = TEXTOS[st.session_state["idioma"]]

  with st.sidebar:
    if foto_blob_user:
      try:
        img = Image.open(io.BytesIO(foto_blob_user))
        st.image(img, width=100)
      except:
        st.write("📷")
    else:
      st.write("👤")

    st.markdown(f"### Olá, {nome_completo_user}")
    st.markdown("---")

    contexto_atual = st.radio(
        "💼 Painel de Gestão",
        [t["sidebar_pessoal"], t["sidebar_profissional"]],
    )
    contexto_limpo = (
        "Profissional" if "Profissional" in contexto_atual else "Pessoal"
    )

    st.markdown("---")

    sel_lang = st.selectbox(
        "🌐 Idioma / Language",
        lista_idiomas,
        index=lista_idiomas.index(st.session_state["idioma"]),
    )
    if sel_lang != st.session_state["idioma"]:
      st.session_state["idioma"] = sel_lang
      st.rerun()

    sel_moeda = st.selectbox(
        "💶 Moeda / Currency",
        list(MOEDAS.keys()),
        index=list(MOEDAS.keys()).index(st.session_state["moeda"]),
    )
    if sel_moeda != st.session_state["moeda"]:
      st.session_state["moeda"] = sel_moeda
      st.rerun()

    st.markdown("---")
    menu = st.radio(
        "Navegação",
        [
            t["nav_overview"],
            t["nav_new"],
            t["nav_manage"],
            t["nav_profile"],
        ],
    )

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button(t["logout"], use_container_width=True):
      st.session_state["logged_in"] = False
      st.session_state["username"] = ""
      st.rerun()

  df_total = carregar_dados(st.session_state["username"])
  df = df_total[df_total["contexto"] == contexto_limpo].copy()

  nome_contexto_traduzido = (
      t["context_profissional"]
      if contexto_limpo == "Profissional"
      else t["context_pessoal"]
  )

  if menu == t["nav_overview"]:
    st.title(f"{t['overview_title']} ({nome_contexto_traduzido})")
    st.write(t["overview_sub"])

    if df.empty:
      mensagem_vazia = t["no_data"].format(
          context=nome_contexto_traduzido, nav_novo=t["nav_novo_label"]
      )
      st.info(mensagem_vazia)
    else:
      df["data"] = pd.to_datetime(df["data"])
      df["mes_ano"] = df["data"].dt.strftime("%Y-%m")

      meses_disponiveis = sorted(df["mes_ano"].unique(), reverse=True)
      mes_selecionado = st.selectbox("📅 Selecione o Mês", meses_disponiveis)

      df_sorted = df.sort_values("data")
      resumo_meses = (
          df_sorted.groupby("mes_ano")
          .apply(
              lambda x: pd.Series({
                  "receitas": x[x["tipo"] == t["types"][1]]["valor"].sum(),
                  "despesas": x[x["tipo"] == t["types"][0]]["valor"].sum(),
                  "investimentos": x[x["tipo"] == t["types"][2]][
                      "valor"
                  ].sum(),
                  "saldo_conta": (
                      x[x["tipo"] == t["types"][1]]["valor"].sum()
                      - x[x["tipo"] == t["types"][0]]["valor"].sum()
                      - x[x["tipo"] == t["types"][2]]["valor"].sum()
                  ),
              })
          )
          .reset_index()
      )

      resumo_meses = resumo_meses.sort_values("mes_ano")
      resumo_meses["saldo_acumulado"] = resumo_meses["saldo_conta"].cumsum()
      resumo_meses["investimentos_acumulados"] = resumo_meses[
          "investimentos"
      ].cumsum()

      saldo_acumulado_atual = (
          resumo_meses.loc[
              resumo_meses["mes_ano"] == mes_selecionado, "saldo_acumulado"
          ].values[0]
          if not resumo_meses[
              resumo_meses["mes_ano"] == mes_selecionado
          ].empty
          else 0.0
      )

      investimento_acumulado_atual = (
          resumo_meses.loc[
              resumo_meses["mes_ano"] == mes_selecionado,
              "investimentos_acumulados",
          ].values[0]
          if not resumo_meses[
              resumo_meses["mes_ano"] == mes_selecionado
          ].empty
          else 0.0
      )

      df_mes = df[df["mes_ano"] == mes_selecionado]

      total_receitas = df_mes[df_mes["tipo"] == t["types"][1]]["valor"].sum()
      total_despesas = df_mes[df_mes["tipo"] == t["types"][0]]["valor"].sum()
      total_investimentos = df_mes[df_mes["tipo"] == t["types"][2]][
          "valor"
      ].sum()
      saldo_conta = total_receitas - total_despesas - total_investimentos

      st.markdown(
          f"""
            <div style="display: flex; gap: 15px; margin-bottom: 12px;">
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['total_rev']}</p>
                    <h3 style="margin: 0; font-size: 20px; color: #2ecc71;">{simbolo_moeda} {total_receitas:,.2f}</h3>
                </div>
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['total_exp']}</p>
                    <h3 style="margin: 0; font-size: 20px; color: #e74c3c;">{simbolo_moeda} {total_despesas:,.2f}</h3>
                </div>
            </div>
            <div style="display: flex; gap: 15px; margin-bottom: 12px;">
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['invest_month']}</p>
                    <h3 style="margin: 0; font-size: 20px; color: #3498db;">{simbolo_moeda} {total_investimentos:,.2f}</h3>
                </div>
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['account_balance']}</p>
                    <h3 style="margin: 0; font-size: 20px;">{simbolo_moeda} {saldo_conta:,.2f}</h3>
                </div>
            </div>
            <div style="display: flex; gap: 15px; margin-bottom: 12px;">
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['invest_accumulated']}</p>
                    <h3 style="margin: 0; font-size: 20px;">{simbolo_moeda} {investimento_acumulado_atual:,.2f}</h3>
                </div>
                <div style="flex: 1; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px;">
                    <p style="margin: 0; color: #888; font-size: 13px;">{t['accumulated_balance']}</p>
                    <h3 style="margin: 0; font-size: 20px;">{simbolo_moeda} {saldo_acumulado_atual:,.2f}</h3>
                </div>
            </div>
        """,
          unsafe_allow_html=True,
      )

      st.markdown("---")
      c1, c2 = st.columns(2)
      with c1:
        df_desp = df_mes[df_mes["tipo"] == t["types"][0]]
        if not df_desp.empty:
          fig_pie = px.pie(
              df_desp,
              names="categoria",
              values="valor",
              title=t["pie_title"],
              hole=0.4,
          )
          fig_pie.update_layout(dragmode=False)
          st.plotly_chart(
              fig_pie,
              use_container_width=True,
              config={"displayModeBar": False, "scrollZoom": False},
          )
        else:
          st.info("Sem despesas para exibir no gráfico neste mês.")

      with c2:
        if not df_mes.empty:
          fig_bar = px.bar(
              df_mes,
              x="data",
              y="valor",
              color="tipo",
              title=t["bar_title"],
              barmode="group",
          )
          fig_bar.update_layout(
              dragmode=False,
              xaxis=dict(fixedrange=True),
              yaxis=dict(fixedrange=True),
          )
          st.plotly_chart(
              fig_bar,
              use_container_width=True,
              config={"displayModeBar": False, "scrollZoom": False},
          )
        else:
          st.info("Sem dados para o gráfico.")

      st.subheader(t["recent_list"])
      st.dataframe(df_mes, use_container_width=True)

  elif menu == t["nav_new"]:
    st.title(f"{t['new_title']} ({nome_contexto_traduzido})")
    st.write(t["new_sub"])

    with st.form("form_novo_lancamento"):
      data_lanc = st.date_input(t["date_label"], datetime.date.today())
      tipo_lanc = st.selectbox(t["type_label"], t["types"])
      valor_lanc = st.number_input(
          f"{t['value_label']} ({simbolo_moeda})", min_value=0.0, format="%.2f"
      )

      lista_cat_atual = (
          t["cat_profissional"]
          if contexto_limpo == "Profissional"
          else t["cat_pessoal"]
      )
      cat_lanc = st.selectbox(t["cat_label"], lista_cat_atual)

      desc_lanc = st.text_input(t["desc_label"])

      submit_lanc = st.form_submit_button(t["save_btn"], use_container_width=True)
      if submit_lanc:
        if valor_lanc > 0:
          salvar_lancamento(
              st.session_state["username"],
              str(data_lanc),
              desc_lanc,
              cat_lanc,
              tipo_lanc,
              valor_lanc,
              contexto_limpo,
          )
          st.success(t["success_msg"])
        else:
          st.warning(t["warn_val"])

  elif menu == t["nav_manage"]:
    st.title(f"{t['manage_title']} ({nome_contexto_traduzido})")
    st.write(t["manage_sub"])

    if df.empty:
      st.info(f"Nenhum lançamento encontrado no painel {nome_contexto_traduzido}.")
    else:
      st.dataframe(df, use_container_width=True)
      id_del = st.selectbox("ID do lançamento para excluir", df["id"].tolist())
      if st.button(t["del_btn"]):
        deletar_lancamento(id_del, st.session_state["username"])
        st.success("Lançamento excluído com sucesso!")
        st.rerun()

  elif menu == t["nav_profile"]:
    st.title(t["profile_title"])
    st.write(t["profile_sub"])

    dados_atuais = obter_dados_usuario(st.session_state["username"])
    nome_atual = dados_atuais[0] if dados_atuais and dados_atuais[0] else ""
    end_atual = dados_atuais[1] if dados_atuais and dados_atuais[1] else ""

    with st.form("form_perfil"):
      novo_nome = st.text_input(t["name_label"], value=nome_atual)
      novo_endereco = st.text_input(t["address_label"], value=end_atual)
      nova_senha = st.text_input(t["new_pass_label"], type="password")

      foto_upload = st.file_uploader(t["photo_label"], type=["png", "jpg", "jpeg"])
      remover_foto_check = st.checkbox(t["remove_photo"])

      submit_perfil = st.form_submit_button(
          t["save_profile"], use_container_width=True
      )

      if submit_perfil:
        foto_blob = None
        if foto_upload is not None:
          foto_blob = foto_upload.read()

        if atualizar_perfil(
            st.session_state["username"],
            novo_nome,
            novo_endereco,
            nova_senha,
            foto_blob,
            remover_foto_check,
        ):
          st.success(t["profile_success"])
          st.rerun()
        else:
          st.error(t["profile_error"])
