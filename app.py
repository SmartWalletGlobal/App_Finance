import streamlit as st
import pandas as pd
import sqlite3
import datetime
import plotly.express as px
import hashlib
from PIL import Image
import io

st.set_page_config(
    page_title="Meu Financeiro | Multi-Usuário",
    page_icon="💶",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Injeção das Meta Tags do Open Graph
st.markdown("""
    <head>
        <meta property="og:title" content="Meu Financeiro | Multi-Usuário">
        <meta property="og:description" content="Sistema de gestão financeira online, simples, rápido e seguro.">
        <meta property="og:image" content="https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?q=80&w=1200&auto=format&fit=crop">
    </head>
""", unsafe_allow_html=True)

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    if make_hash(password) == hashed_text:
        return True
    return False

def init_db():
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            username TEXT PRIMARY KEY,
            nome_completo TEXT,
            senha TEXT
        )
    ''')
    for col, col_type in [("endereco", "TEXT"), ("foto_perfil", "BLOB"), ("ramo_atividade", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {col_type}")
        except:
            pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            data TEXT,
            descricao TEXT,
            categoria TEXT,
            tipo TEXT,
            valor REAL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE lancamentos ADD COLUMN username TEXT")
    except:
        pass

    conn.commit()
    conn.close()

init_db()

def cadastrar_usuario(username, nome_completo, senha, ramo_atividade="Outros"):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (username, nome_completo, senha, ramo_atividade) VALUES (?, ?, ?, ?)", 
                       (username, nome_completo, make_hash(senha), ramo_atividade))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def autenticar_usuario(username, senha):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT senha FROM usuarios WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return check_hash(senha, result[0])
    return False

def obter_dados_usuario(username):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nome_completo, endereco, foto_perfil, ramo_atividade FROM usuarios WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result

def atualizar_perfil(username, novo_nome, novo_endereco, nova_senha, nova_foto_blob, novo_ramo, remover_foto=False):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    try:
        if remover_foto:
            foto_sql = None
        else:
            foto_sql = nova_foto_blob

        if nova_senha:
            hash_senha = make_hash(nova_senha)
            if remover_foto:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ?, foto_perfil = NULL, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, hash_senha, novo_ramo, username))
            elif nova_foto_blob is not None:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ?, foto_perfil = ?, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, hash_senha, nova_foto_blob, novo_ramo, username))
            else:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, senha = ?, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, hash_senha, novo_ramo, username))
        else:
            if remover_foto:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, foto_perfil = NULL, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, novo_ramo, username))
            elif nova_foto_blob is not None:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, foto_perfil = ?, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, nova_foto_blob, novo_ramo, username))
            else:
                cursor.execute("UPDATE usuarios SET nome_completo = ?, endereco = ?, ramo_atividade = ? WHERE username = ?", 
                               (novo_nome, novo_endereco, novo_ramo, username))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def carregar_dados(username):
    conn = sqlite3.connect('financeiro.db')
    df = pd.read_sql_query("SELECT * FROM lancamentos WHERE username = ?", conn, params=(username,))
    conn.close()
    return df

def salvar_lancamento(username, data, descricao, categoria, tipo, valor):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO lancamentos (username, data, descricao, categoria, tipo, valor) VALUES (?, ?, ?, ?, ?, ?)",
                   (username, data, descricao, categoria, tipo, valor))
    conn.commit()
    conn.close()

def deletar_lancamento(id_lancamento, username):
    conn = sqlite3.connect('financeiro.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lancamentos WHERE id = ? AND username = ?", (id_lancamento, username))
    conn.commit()
    conn.close()

# Dicionários traduzidos de cabo a rabo para Ramos e Categorias
TRADUCOES_RAMOS = {
    "Português": {
        "mecanica": "🛠️ Mecânica / Oficina",
        "obras": "🏗️ Obras / Construção",
        "ti": "💻 TI / Desenvolvimento",
        "comercio": "🛍️ Comércio / Loja",
        "outros": "📋 Outros / Geral",
        "cat_mecanica_desp": ["Peças / Insumos", "Ferramentas", "Equipamentos", "Manutenção Predial", "Aluguel", "Impostos / Taxas", "Outras Despesas"],
        "cat_mecanica_rec": ["Pagamento de Clientes", "Serviços Realizados", "Venda de Peças", "Orçamentos Aprovados", "Outras Receitas"],
        "cat_obras_desp": ["Materiais de Construção", "Ferramentas", "Equipamentos", "Mão de Obra / Subcontratados", "Combustível / Frete", "Outras Despesas"],
        "cat_obras_rec": ["Medição de Obra", "Pagamento de Clientes", "Adiantamento / Sinal", "Venda de Sobras", "Outras Receitas"],
        "cat_ti_desp": ["Softwares / Assinaturas", "Hospedagem / Servidores", "Equipamentos", "Marketing", "Cursos / Capacitação", "Outras Despesas"],
        "cat_ti_rec": ["Desenvolvimento de Projetos", "Consultoria", "Suporte Mensal (Retainer)", "Outras Receitas"],
        "cat_comercio_desp": ["Aquisição de Mercadorias", "Embalagens", "Frete / Logística", "Marketing / Anúncios", "Aluguel", "Outras Despesas"],
        "cat_comercio_rec": ["Vendas à Vista", "Vendas no Cartão / Pix", "Vendas Parceladas", "Outras Receitas"],
        "cat_outros_desp": ["Aluguel", "Alimentação", "Transporte", "Serviços", "Impostos", "Outras Despesas"],
        "cat_outros_rec": ["Salário", "Prestação de Serviços", "Vendas", "Outras Receitas"],
        "tipo_despesa": "Despesa",
        "tipo_receita": "Receita"
    },
    "English": {
        "mecanica": "🛠️ Mechanics / Workshop",
        "obras": "🏗️ Construction / Building",
        "ti": "💻 IT / Development",
        "comercio": "🛍️ Retail / Store",
        "outros": "📋 Others / General",
        "cat_mecanica_desp": ["Parts / Supplies", "Tools", "Equipment", "Building Maintenance", "Rent", "Taxes / Fees", "Other Expenses"],
        "cat_mecanica_rec": ["Client Payments", "Services Rendered", "Parts Sales", "Approved Budgets", "Other Income"],
        "cat_obras_desp": ["Building Materials", "Tools", "Equipment", "Labor / Subcontractors", "Fuel / Freight", "Other Expenses"],
        "cat_obras_rec": ["Construction Measurement", "Client Payments", "Advance / Deposit", "Surplus Sales", "Other Income"],
        "cat_ti_desp": ["Software / Subscriptions", "Hosting / Servers", "Equipment", "Marketing", "Courses / Training", "Other Expenses"],
        "cat_ti_rec": ["Project Development", "Consulting", "Monthly Support (Retainer)", "Other Income"],
        "cat_comercio_desp": ["Goods Acquisition", "Packaging", "Freight / Logistics", "Marketing / Ads", "Rent", "Other Expenses"],
        "cat_comercio_rec": ["Cash Sales", "Card / Pix Sales", "Installment Sales", "Other Income"],
        "cat_outros_desp": ["Rent", "Food", "Transport", "Services", "Taxes", "Other Expenses"],
        "cat_outros_rec": ["Salary", "Service Provision", "Sales", "Other Income"],
        "tipo_despesa": "Expense",
        "tipo_receita": "Income"
    },
    "Français": {
        "mecanica": "🛠️ Mécanique / Atelier",
        "obras": "🏗️ Bâtiment / Construction",
        "ti": "💻 Informatique / Développement",
        "comercio": "🛍️ Commerce / Magasin",
        "outros": "📋 Autres / Général",
        "cat_mecanica_desp": ["Pièces / Consommables", "Outils", "Équipement", "Maintenance des Locaux", "Loyer", "Impôts / Taxes", "Autres Dépenses"],
        "cat_mecanica_rec": ["Paiement des Clients", "Services Réalisés", "Vente de Pièces", "Devis Approuvés", "Autres Revenus"],
        "cat_obras_desp": ["Matériaux de Construction", "Outils", "Équipement", "Main-d'œuvre / Sous-traitants", "Carburant / Fret", "Autres Dépenses"],
        "cat_obras_rec": ["Mesurage de Chantier", "Paiement des Clients", "Acompte / Avance", "Vente de Surplus", "Autres Revenus"],
        "cat_ti_desp": ["Logiciels / Abonnements", "Hébergement / Serveurs", "Équipement", "Marketing", "Formations", "Autres Dépenses"],
        "cat_ti_rec": ["Développement de Projets", "Conseil", "Support Mensuel (Retainer)", "Autres Revenus"],
        "cat_comercio_desp": ["Achat de Marchandises", "Emballages", "Fret / Logistique", "Marketing / Publicité", "Loyer", "Autres Dépenses"],
        "cat_comercio_rec": ["Ventes au Comptant", "Ventes Carte / Pix", "Ventes Échelonnées", "Autres Revenus"],
        "cat_outros_desp": ["Loyer", "Alimentation", "Transport", "Services", "Impôts", "Autres Dépenses"],
        "cat_outros_rec": ["Salaire", "Prestation de Services", "Ventes", "Autres Revenus"],
        "tipo_despesa": "Dépense",
        "tipo_receita": "Revenu"
    },
    "Español": {
        "mecanica": "🛠️ Mecánica / Taller",
        "obras": "🏗️ Obras / Construcción",
        "ti": "💻 TI / Desarrollo",
        "comercio": "🛍️ Comercio / Tienda",
        "outros": "📋 Otros / General",
        "cat_mecanica_desp": ["Piezas / Insumos", "Herramientas", "Equipos", "Mantenimiento", "Alquiler", "Impuestos / Tasas", "Otros Gastos"],
        "cat_mecanica_rec": ["Pago de Clientes", "Servicios Realizados", "Venta de Piezas", "Presupuestos Aprobados", "Otros Ingresos"],
        "cat_obras_desp": ["Materiales de Construcción", "Herramientas", "Equipos", "Mano de Obra / Subcontratados", "Combustible / Flete", "Otros Gastos"],
        "cat_obras_rec": ["Medición de Obra", "Pago de Clientes", "Anticipo / Seña", "Venta de Sobrantes", "Otros Ingresos"],
        "cat_ti_desp": ["Software / Suscripciones", "Hosting / Servidores", "Equipos", "Marketing", "Cursos / Capacitación", "Otros Gastos"],
        "cat_ti_rec": ["Desarrollo de Proyectos", "Consultoría", "Soporte Mensual", "Otros Ingresos"],
        "cat_comercio_desp": ["Adquisición de Mercancías", "Embalajes", "Flete / Logística", "Marketing / Anuncios", "Alquiler", "Otros Gastos"],
        "cat_comercio_rec": ["Ventas al Contado", "Ventas con Tarjeta / Pix", "Ventas en Cuotas", "Otros Ingresos"],
        "cat_outros_desp": ["Alquiler", "Alimentación", "Transporte", "Servicios", "Impuestos", "Otros Gastos"],
        "cat_outros_rec": ["Salario", "Prestación de Servicios", "Ventas", "Otros Ingresos"],
        "tipo_despesa": "Gasto",
        "tipo_receita": "Ingreso"
    },
    "Italiano": {
        "mecanica": "🛠️ Meccanica / Officina",
        "obras": "🏗️ Edilizia / Costruzione",
        "ti": "💻 IT / Sviluppo",
        "comercio": "🛍️ Commercio / Negozio",
        "outros": "📋 Altro / Generale",
        "cat_mecanica_desp": ["Ricambi / Materiali", "Utensili", "Attrezzatura", "Manutenzione", "Affitto", "Tasse / Imposte", "Altre Spese"],
        "cat_mecanica_rec": ["Pagamenti Clienti", "Servizi Eseguiti", "Vendita Ricambi", "Preventivi Approvati", "Altre Entrate"],
        "cat_obras_desp": ["Materiali Edili", "Utensili", "Attrezzatura", "Manodopera / Subappalti", "Carburante / Trasporto", "Altre Spese"],
        "cat_obras_rec": ["Stato Avanzamento Lavori", "Pagamenti Clienti", "Acconto", "Vendita Surplus", "Altre Entrate"],
        "cat_ti_desp": ["Software / Abbonamenti", "Hosting / Server", "Attrezzatura", "Marketing", "Corsi / Formazione", "Altre Spese"],
        "cat_ti_rec": ["Sviluppo Progetti", "Consulenza", "Supporto Mensile", "Altre Entrate"],
        "cat_comercio_desp": ["Acquisto Merce", "Imballaggi", "Spedizione / Logistica", "Marketing / Annunci", "Affitto", "Altre Spese"],
        "cat_comercio_rec": ["Vendite in Contanti", "Vendite Carta / Pix", "Vendite Rateali", "Altre Entrate"],
        "cat_outros_desp": ["Affitto", "Alimentazione", "Trasporto", "Servizi", "Tasse", "Altre Spese"],
        "cat_outros_rec": ["Stipendio", "Prestazione Servizi", "Vendite", "Altre Entrate"],
        "tipo_despesa": "Spesa",
        "tipo_receita": "Entrata"
    },
    "Deutsch": {
        "mecanica": "🛠️ Mechanik / Werkstatt",
        "obras": "🏗️ Bauwesen / Konstruktion",
        "ti": "💻 IT / Entwicklung",
        "comercio": "🛍️ Handel / Geschäft",
        "outros": "📋 Sonstiges / Allgemein",
        "cat_mecanica_desp": ["Teile / Verbrauchsmaterial", "Werkzeuge", "Ausstattung", "Gebäudewartung", "Miete", "Steuern / Gebühren", "Sonstige Ausgaben"],
        "cat_mecanica_rec": ["Kundenzahlungen", "Erbrachte Dienstleistungen", "Teileverkauf", "Genehmigte Budgets", "Sonstige Einnahmen"],
        "cat_obras_desp": ["Baumaterialien", "Werkzeuge", "Ausstattung", "Arbeitskräfte / Subunternehmer", "Kraftstoff / Fracht", "Sonstige Ausgaben"],
        "cat_obras_rec": ["Bauabrechnung", "Kundenzahlungen", "Vorschuss / Anzahlung", "Restverkauf", "Sonstige Einnahmen"],
        "cat_ti_desp": ["Software / Abonnements", "Hosting / Server", "Ausstattung", "Marketing", "Kurse / Schulungen", "Sonstige Ausgaben"],
        "cat_ti_rec": ["Projektentwicklung", "Beratung", "Monatlicher Support", "Sonstige Einnahmen"],
        "cat_comercio_desp": ["Warenerwerb", "Verpackung", "Fracht / Logistik", "Marketing / Werbung", "Miete", "Sonstige Ausgaben"],
        "cat_comercio_rec": ["Barverkäufe", "Kartenzahlung / Pix", "Ratenverkäufe", "Sonstige Einnahmen"],
        "cat_outros_desp": ["Miete", "Verpflegung", "Transport", "Dienstleistungen", "Steuern", "Sonstige Ausgaben"],
        "cat_outros_rec": ["Gehalt", "Dienstleistung", "Verkäufe", "Sonstige Einnahmen"],
        "tipo_despesa": "Ausgabe",
        "tipo_receita": "Einnahme"
    }
}

TEXTOS = {
    "Português": {
        "login_title": "Acesso ao Meu Financeiro",
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
        "reg_branch_label": "Ramo de Atuação / Negócio",
        "btn_reg_submit": "Cadastrar Nova Conta",
        "reg_warn": "Preencha todos os campos.",
        "reg_success": "Conta criada com sucesso! Vá na aba 'Entrar'.",
        "reg_error": "Este usuário já existe ou ocorreu uma falha no cadastro.",
        "nav_overview": "📊 Visão Geral & Gráficos",
        "nav_business": "💼 Painel Profissional (Business)",
        "nav_new": "➕ Novo Lançamento",
        "nav_manage": "✏️ Gerenciar & Editar",
        "nav_profile": "👤 Meu Perfil",
        "overview_title": "Visão Geral Financeira",
        "overview_sub": "Acompanhe seus fluxos, receitas e despesas por mês.",
        "business_title": "💼 Painel Profissional e Gestão de Negócios",
        "business_sub": "Análise financeira focada no seu segmento de mercado.",
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
        "profile_sub": "Atualize suas informações cadastrais, senha, ramo ou foto de perfil.",
        "name_label": "Nome Completo",
        "address_label": "Endereço",
        "new_pass_label": "Nova Senha (deixe em branco para não alterar)",
        "photo_label": "Foto de Perfil",
        "remove_photo": "Remover foto atual",
        "save_profile": "Salvar Alterações",
        "profile_success": "Perfil atualizado com sucesso!",
        "profile_error": "Erro ao atualizar perfil.",
        "logout": "🚪 Sair da Conta",
        "lang_label": "🌐 Idioma",
        "curr_label": "💶 Moeda",
        "gross_rev": "📈 Faturamento Bruto",
        "operating_costs": "📉 Custos / Despesas",
        "net_profit": "💎 Lucro Líquido",
        "profit_margin": "📊 Margem de Lucro",
        "rec_cat_biz": "📊 Receitas por Categoria (Negócio)",
        "origin_rev": "Origem do Faturamento",
        "op_costs_biz": "🛠️ Custos Operacionais / Insumos",
        "highest_costs": "Maiores Custos por Categoria",
        "biz_report": "📋 Relatório Analítico de Lançamentos do Negócio",
        "id_del_label": "ID do lançamento para excluir",
        "del_success": "Lançamento excluído com sucesso!"
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
        "reg_branch_label": "Business Industry / Sector",
        "btn_reg_submit": "Register New Account",
        "reg_warn": "Please fill in all fields.",
        "reg_success": "Account created successfully! Go to 'Log In'.",
        "reg_error": "This user already exists or registration failed.",
        "nav_overview": "📊 Overview & Charts",
        "nav_business": "💼 Professional Panel (Business)",
        "nav_new": "➕ New Entry",
        "nav_manage": "✏️ Manage & Edit",
        "nav_profile": "👤 My Profile",
        "overview_title": "Financial Overview",
        "overview_sub": "Track your cash flows, income, and expenses by month.",
        "business_title": "💼 Professional Panel & Business Management",
        "business_sub": "Financial analytics focused on your market sector.",
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
        "profile_sub": "Update your profile info, password, sector, or picture.",
        "name_label": "Full Name",
        "address_label": "Address",
        "new_pass_label": "New Password (leave blank to keep current)",
        "photo_label": "Profile Picture",
        "remove_photo": "Remove current picture",
        "save_profile": "Save Changes",
        "profile_success": "Profile updated successfully!",
        "profile_error": "Error updating profile.",
        "logout": "🚪 Log Out",
        "lang_label": "🌐 Language",
        "curr_label": "💶 Currency",
        "gross_rev": "📈 Gross Revenue",
        "operating_costs": "📉 Costs / Expenses",
        "net_profit": "💎 Net Profit",
        "profit_margin": "📊 Profit Margin",
        "rec_cat_biz": "📊 Income by Category (Business)",
        "origin_rev": "Revenue Origin",
        "op_costs_biz": "🛠️ Operating Costs / Inputs",
        "highest_costs": "Highest Costs by Category",
        "biz_report": "📋 Business Analytical Entry Report",
        "id_del_label": "Entry ID to delete",
        "del_success": "Entry deleted successfully!"
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
        "reg_branch_label": "Secteur d'activité",
        "btn_reg_submit": "Créer le compte",
        "reg_warn": "Veuillez remplir tous les champs.",
        "reg_success": "Compte créé avec succès ! Allez dans l'onglet 'Connexion'.",
        "reg_error": "Cet utilisateur existe déjà ou une erreur est survenue.",
        "nav_overview": "📊 Vue d'ensemble",
        "nav_business": "💼 Tableau de Bord Pro",
        "nav_new": "➕ Nouvelle Entrée",
        "nav_manage": "✏️ Gérer & Éditer",
        "nav_profile": "👤 Mon Profil",
        "overview_title": "Vue d'ensemble financière",
        "overview_sub": "Suivez vos flux, revenus et dépenses par mois.",
        "business_title": "💼 Tableau de Bord Professionnel",
        "business_sub": "Analyse financière axée sur votre secteur d'activité.",
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
        "lang_label": "🌐 Langue",
        "curr_label": "💶 Devise",
        "gross_rev": "📈 Chiffre d'Affaires Brut",
        "operating_costs": "📉 Coûts / Dépenses",
        "net_profit": "💎 Bénéfice Net",
        "profit_margin": "📊 Marge Bénéficiaire",
        "rec_cat_biz": "📊 Revenus par Catégorie (Business)",
        "origin_rev": "Origine du Chiffre d'Affaires",
        "op_costs_biz": "🛠️ Coûts Opérationnels / Intrants",
        "highest_costs": "Coûts les Plus Élevés par Catégorie",
        "biz_report": "📋 Rapport Analytique des Entrées Business",
        "id_del_label": "ID de l'entrée à supprimer",
        "del_success": "Entrée supprimée avec succès !"
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
        "reg_branch_label": "Rubro / Sector Comercial",
        "btn_reg_submit": "Crear Cuenta Nueva",
        "reg_warn": "Por favor llena todos los campos.",
        "reg_success": "¡Cuenta creada con éxito! Ve a la pestaña 'Entrar'.",
        "reg_error": "Este usuario ya existe o hubo un error.",
        "nav_overview": "📊 Visión General y Gráficos",
        "nav_business": "💼 Panel Profesional (Business)",
        "nav_new": "➕ Nuevo Movimiento",
        "nav_manage": "✏️ Gestionar y Editar",
        "nav_profile": "👤 Mi Perfil",
        "overview_title": "Resumen Financiero",
        "overview_sub": "Sigue tus ingresos y gastos por mes.",
        "business_title": "💼 Panel Profesional y Gestión de Negocios",
        "business_sub": "Análisis financiero enfocado en tu sector de mercado.",
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
        "lang_label": "🌐 Idioma",
        "curr_label": "💶 Moneda",
        "gross_rev": "📈 Facturación Bruta",
        "operating_costs": "📉 Costos / Gastos",
        "net_profit": "💎 Beneficio Neto",
        "profit_margin": "📊 Margen de Beneficio",
        "rec_cat_biz": "📊 Ingresos por Categoría (Negocio)",
        "origin_rev": "Origen de la Facturación",
        "op_costs_biz": "🛠️ Costos Operativos / Insumos",
        "highest_costs": "Mayores Costos por Categoría",
        "biz_report": "📋 Reporte Analítico de Movimientos del Negocio",
        "id_del_label": "ID del movimiento a eliminar",
        "del_success": "¡Movimiento eliminado con éxito!"
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
        "login_error": "Utente o password non errati.",
        "reg_user_label": "Definisci un nome utente",
        "reg_name_label": "Il tuo Nome Completo",
        "reg_pass_label": "Scegli una Password",
        "reg_branch_label": "Settore di Attività",
        "btn_reg_submit": "Registra Nuovo Account",
        "reg_warn": "Compila tutti i campi.",
        "reg_success": "Account creato con successo! Vai su 'Accedi'.",
        "reg_error": "Utente già esistente o errore di registrazione.",
        "nav_overview": "📊 Panoramica & Grafici",
        "nav_business": "💼 Pannello Professionale",
        "nav_new": "➕ Nuova Voce",
        "nav_manage": "✏️ Gestisci & Modifica",
        "nav_profile": "👤 Il Mio Profilo",
        "overview_title": "Panoramica Finanziaria",
        "overview_sub": "Monitora flussi, entrate e spese per mese.",
        "business_title": "💼 Pannello Professionale & Business",
        "business_sub": "Analisi finanziaria mirata per il tuo settore.",
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
        "lang_label": "🌐 Lingua",
        "curr_label": "💶 Valuta",
        "gross_rev": "📈 Fatturato Lordo",
        "operating_costs": "📉 Costi / Spese",
        "net_profit": "💎 Utile Netto",
        "profit_margin": "📊 Margine di Profitto",
        "rec_cat_biz": "📊 Entrate per Categoria (Business)",
        "origin_rev": "Origine del Fatturato",
        "op_costs_biz": "🛠️ Costi Operativi / Materiali",
        "highest_costs": "Costi Maggiori per Categoria",
        "biz_report": "📋 Report Analitico Voci Business",
        "id_del_label": "ID voce da eliminare",
        "del_success": "Voce eliminata con successo!"
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
        "reg_branch_label": "Geschäftsbereich / Branche",
        "btn_reg_submit": "Konto erstellen",
        "reg_warn": "Bitte füllen Sie alle Felder aus.",
        "reg_success": "Konto erfolgreich erstellt! Gehen Sie zu 'Anmelden'.",
        "reg_error": "Benutzer existiert bereits oder Fehler.",
        "nav_overview": "📊 Übersicht & Diagramme",
        "nav_business": "💼 Business-Dashboard",
        "nav_new": "➕ Neuer Eintrag",
        "nav_manage": "✏️ Verwalten & Bearbeiten",
        "nav_profile": "👤 Mein Profil",
        "overview_title": "Finanzübersicht",
        "overview_sub": "Verfolgen Sie Einnahmen und Ausgaben nach Monat.",
        "business_title": "💼 Business-Dashboard & Unternehmensfinanzen",
        "business_sub": "Finanzanalysen zugeschnitten auf Ihre Branche.",
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
        "lang_label": "🌐 Sprache",
        "curr_label": "💶 Währung",
        "gross_rev": "📈 Bruttoumsatz",
        "operating_costs": "📉 Kosten / Ausgaben",
        "net_profit": "💎 Nettogewinn",
        "profit_margin": "📊 Gewinnmarge",
        "rec_cat_biz": "📊 Einnahmen nach Kategorie (Business)",
        "origin_rev": "Umsatzursprung",
        "op_costs_biz": "🛠️ Betriebskosten / Verbrauchsmaterial",
        "highest_costs": "Höchste Kosten nach Kategorie",
        "biz_report": "📋 Analytischer Business-Eintragsbericht",
        "id_del_label": "Eintrags-ID zum Löschen",
        "del_success": "Eintrag erfolgreich gelöscht!"
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
t_login = TEXTOS[st.session_state['idioma']]
ramos_atuais_dict = TRADUCOES_RAMOS[st.session_state['idioma']]

if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h2 style='text-align: center;'>{t_login['login_title']}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>{t_login['login_sub']}</p>", unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs([t_login['tab_login'], t_login['tab_register']])
        
        with tab_login:
            with st.form("form_login"):
                u_input = st.text_input(t_login['user_label'])
                p_input = st.text_input(t_login['pass_label'], type="password")
                submit_login = st.form_submit_button(t_login['btn_login_submit'], use_container_width=True)
                
                if submit_login:
                    if autenticar_usuario(u_input, p_input):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u_input
                        st.success(t_login['login_success'])
                        st.rerun()
                    else:
                        st.error(t_login['login_error'])
                        
        with tab_reg:
            with st.form("form_reg"):
                reg_user = st.text_input(t_login['reg_user_label'])
                reg_name = st.text_input(t_login['reg_name_label'])
                reg_pass = st.text_input(t_login['reg_pass_label'], type="password")
                
                opcoes_ramos_reg = [
                    ramos_atuais_dict["mecanica"],
                    ramos_atuais_dict["obras"],
                    ramos_atuais_dict["ti"],
                    ramos_atuais_dict["comercio"],
                    ramos_atuais_dict["outros"]
                ]
                reg_branch_ui = st.selectbox(t_login['reg_branch_label'], opcoes_ramos_reg)
                
                # Mapeia de volta para a chave padrão interna para salvar no banco
                mapa_inverso_ramos = {v: k for k, v in ramos_atuais_dict.items() if k in ["mecanica", "obras", "ti", "comercio", "outros"]}
                
                submit_reg = st.form_submit_button(t_login['btn_reg_submit'], use_container_width=True)
                
                if submit_reg:
                    if reg_user and reg_name and reg_pass:
                        chave_ramo = "outros"
                        for k, v in ramos_atuais_dict.items():
                            if v == reg_branch_ui:
                                chave_ramo = k
                                break
                        if cadastrar_usuario(reg_user, reg_name, reg_pass, chave_ramo):
                            st.success(t_login['reg_success'])
                        else:
                            st.error(t_login['reg_error'])
                    else:
                        st.warning(t_login['reg_warn'])

        st.markdown("<hr>", unsafe_allow_html=True)
        sel_lang = st.selectbox(t_login['lang_label'], lista_idiomas, index=lista_idiomas.index(st.session_state['idioma']))
        if sel_lang != st.session_state['idioma']:
            st.session_state['idioma'] = sel_lang
            st.rerun()

        sel_moeda = st.selectbox(t_login['curr_label'], list(MOEDAS.keys()), index=list(MOEDAS.keys()).index(st.session_state['moeda']))
        if sel_moeda != st.session_state['moeda']:
            st.session_state['moeda'] = sel_moeda
            st.rerun()

else:
    dados_user = obter_dados_usuario(st.session_state['username'])
    nome_completo_user = dados_user[0] if dados_user and dados_user[0] else st.session_state['username']
    foto_blob_user = dados_user[2] if dados_user and len(dados_user) > 2 else None
    ramo_usuario_db = dados_user[3] if dados_user and len(dados_user) > 3 and dados_user[3] else "outros"

    simbolo_moeda = MOEDAS[st.session_state['moeda']]
    t = TEXTOS[st.session_state['idioma']]
    ramos_dict = TRADUCOES_RAMOS[st.session_state['idioma']]

    ramo_usuario_exibicao = ramos_dict.get(ramo_usuario_db, ramos_dict["outros"])

    with st.sidebar:
        if foto_blob_user:
            try:
                img = Image.open(io.BytesIO(foto_blob_user))
                st.image(img, width=100)
            except:
                st.write("📷")
        else:
            st.write("👤")

        st.markdown(f"### ⚡ Olá, {nome_completo_user}")
        st.caption(f"💼 {ramo_usuario_exibicao}")
        st.markdown("---")

        sel_lang = st.selectbox(t['lang_label'], lista_idiomas, index=lista_idiomas.index(st.session_state['idioma']))
        if sel_lang != st.session_state['idioma']:
            st.session_state['idioma'] = sel_lang
            st.rerun()

        sel_moeda = st.selectbox(t['curr_label'], list(MOEDAS.keys()), index=list(MOEDAS.keys()).index(st.session_state['moeda']))
        if sel_moeda != st.session_state['moeda']:
            st.session_state['moeda'] = sel_moeda
            st.rerun()

        st.markdown("---")
        menu = st.radio("Navegação", [
            t['nav_overview'],
            t['nav_business'],
            t['nav_new'],
            t['nav_manage'],
            t['nav_profile']
        ])

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button(t['logout'], use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.rerun()

    df = carregar_dados(st.session_state['username'])

    if menu == t['nav_overview']:
        st.title(t['overview_title'])
        st.write(t['overview_sub'])

        if df.empty:
            st.info(t['no_data'])
        else:
            df["data"] = pd.to_datetime(df["data"])
            df["mes_ano"] = df["data"].dt.strftime("%Y-%m")
            
            meses_disponiveis = sorted(df["mes_ano"].unique(), reverse=True)
            mes_selecionado = st.selectbox("📅 Selecione o Mês", meses_disponiveis)
            
            df_mes = df[df["mes_ano"] == mes_selecionado]

            total_receitas = df_mes[df_mes['tipo'] == ramos_dict["tipo_receita"]]['valor'].sum()
            total_despesas = df_mes[df_mes['tipo'] == ramos_dict["tipo_despesa"]]['valor'].sum()
            saldo = total_receitas - total_despesas

            col1, col2, col3 = st.columns(3)
            col1.metric(t['total_rev'], f"{simbolo_moeda} {total_receitas:,.2f}")
            col2.metric(t['total_exp'], f"{simbolo_moeda} {total_despesas:,.2f}")
            col3.metric(t['balance'], f"{simbolo_moeda} {saldo:,.2f}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                df_desp = df_mes[df_mes['tipo'] == ramos_dict["tipo_despesa"]]
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

    elif menu == t['nav_business']:
        st.title(t['business_title'])
        st.write(f"{t['business_sub']} — **Setor: {ramo_usuario_exibicao}**")

        if df.empty:
            st.info(t['no_data'])
        else:
            df["data"] = pd.to_datetime(df["data"])
            df["mes_ano"] = df["data"].dt.strftime("%Y-%m")
            
            meses_disponiveis = sorted(df["mes_ano"].unique(), reverse=True)
            mes_selecionado = st.selectbox("📅 Mês de Análise (Business)", meses_disponiveis, key="sel_mes_biz")
            
            df_mes = df[df["mes_ano"] == mes_selecionado]

            faturamento = df_mes[df_mes['tipo'] == ramos_dict["tipo_receita"]]['valor'].sum()
            custos = df_mes[df_mes['tipo'] == ramos_dict["tipo_despesa"]]['valor'].sum()
            lucro_liquido = faturamento - custos
            margem = (lucro_liquido / faturamento * 100) if faturamento > 0 else 0.0

            col1, col2, col3, col4 = st.columns(4)
            col1.metric(t['gross_rev'], f"{simbolo_moeda} {faturamento:,.2f}")
            col2.metric(t['operating_costs'], f"{simbolo_moeda} {custos:,.2f}")
            col3.metric(t['net_profit'], f"{simbolo_moeda} {lucro_liquido:,.2f}")
            col4.metric(t['profit_margin'], f"{margem:.1f}%")

            st.markdown("---")
            
            bc1, bc2 = st.columns(2)
            with bc1:
                st.subheader(t['rec_cat_biz'])
                df_rec = df_mes[df_mes['tipo'] == ramos_dict["tipo_receita"]]
                if not df_rec.empty:
                    fig_rec = px.pie(df_rec, names='categoria', values='valor', title=t['origin_rev'], hole=0.4)
                    st.plotly_chart(fig_rec, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Nenhuma receita registrada neste mês.")

            with bc2:
                st.subheader(t['op_costs_biz'])
                df_desp = df_mes[df_mes['tipo'] == ramos_dict["tipo_despesa"]]
                if not df_desp.empty:
                    fig_desp = px.bar(df_desp, x='categoria', y='valor', title=t['highest_costs'], color='categoria')
                    st.plotly_chart(fig_desp, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Nenhuma despesa registrada neste mês.")

            st.subheader(t['biz_report'])
            st.dataframe(df_mes[['data', 'tipo', 'categoria', 'descricao', 'valor']], use_container_width=True)

    elif menu == t['nav_new']:
        st.title(t['new_title'])
        st.write(t['new_sub'])

        # Seleciona as listas de categorias com base no ramo do usuário e idioma atual
        if ramo_usuario_db == "mecanica":
            lista_desp_cat = ramos_dict["cat_mecanica_desp"]
            lista_rec_cat = ramos_dict["cat_mecanica_rec"]
        elif ramo_usuario_db == "obras":
            lista_desp_cat = ramos_dict["cat_obras_desp"]
            lista_rec_cat = ramos_dict["cat_obras_rec"]
        elif ramo_usuario_db == "ti":
            lista_desp_cat = ramos_dict["cat_ti_desp"]
            lista_rec_cat = ramos_dict["cat_ti_rec"]
        elif ramo_usuario_db == "comercio":
            lista_desp_cat = ramos_dict["cat_comercio_desp"]
            lista_rec_cat = ramos_dict["cat_comercio_rec"]
        else:
            lista_desp_cat = ramos_dict["cat_outros_desp"]
            lista_rec_cat = ramos_dict["cat_outros_rec"]

        with st.form("form_novo_lancamento"):
            data_lanc = st.date_input(t['date_label'], datetime.date.today())
            
            tipo_opcoes = [ramos_dict["tipo_despesa"], ramos_dict["tipo_receita"]]
            tipo_lanc_ui = st.selectbox(t['type_label'], tipo_opcoes)
            
            valor_lanc = st.number_input(f"{t['value_label']} ({simbolo_moeda})", min_value=0.0, format="%.2f")
            
            opcoes_cat = lista_desp_cat if tipo_lanc_ui == ramos_dict["tipo_despesa"] else lista_rec_cat
            cat_lanc = st.selectbox(t['cat_label'], opcoes_cat)
            
            desc_lanc = st.text_input(t['desc_label'])
            
            submit_lanc = st.form_submit_button(t['save_btn'], use_container_width=True)
            if submit_lanc:
                if desc_lanc.strip() != "":
                    salvar_lancamento(st.session_state['username'], str(data_lanc), desc_lanc, cat_lanc, tipo_lanc_ui, valor_lanc)
                    st.success(t['success_msg'])
                else:
                    st.warning(t['warn_desc'])

    elif menu == t['nav_manage']:
        st.title(t['manage_title'])
        st.write(t['manage_sub'])

        if df.empty:
            st.info(t['no_data'])
        else:
            st.dataframe(df, use_container_width=True)
            id_del = st.selectbox(t['id_del_label'], df['id'].tolist())
            if st.button(t['del_btn']):
                deletar_lancamento(id_del, st.session_state['username'])
                st.success(t['del_success'])
                st.rerun()

    elif menu == t['nav_profile']:
        st.title(t['profile_title'])
        st.write(t['profile_sub'])

        dados_atuais = obter_dados_usuario(st.session_state['username'])
        nome_atual = dados_atuais[0] if dados_atuais and dados_atuais[0] else ""
        end_atual = dados_atuais[1] if dados_atuais and dados_atuais[1] else ""
        ramo_atual_db = dados_atuais[3] if dados_atuais and len(dados_atuais) > 3 and dados_atuais[3] else "outros"

        opcoes_ramos_perfil = [
            ramos_dict["mecanica"],
            ramos_dict["obras"],
            ramos_dict["ti"],
            ramos_dict["comercio"],
            ramos_dict["outros"]
        ]
        
        # Encontra o índice atual para o selectbox
        ramo_atual_ui = ramos_dict.get(ramo_atual_db, ramos_dict["outros"])
        idx_ramo = opcoes_ramos_perfil.index(ramo_atual_ui) if ramo_atual_ui in opcoes_ramos_perfil else 0

        with st.form("form_perfil"):
            novo_nome = st.text_input(t['name_label'], value=nome_atual)
            novo_endereco = st.text_input(t['address_label'], value=end_atual)
            novo_ramo_ui = st.selectbox(t['reg_branch_label'], opcoes_ramos_perfil, index=idx_ramo)
            nova_senha = st.text_input(t['new_pass_label'], type="password")
            
            foto_upload = st.file_uploader(t['photo_label'], type=["png", "jpg", "jpeg"])
            remover_foto_check = st.checkbox(t['remove_photo'])

            submit_perfil = st.form_submit_button(t['save_profile'], use_container_width=True)

            if submit_perfil:
                foto_blob = None
                if foto_upload is not None:
                    foto_blob = foto_upload.read()
                
                # Mapeia a seleção de volta para a chave padrão interna
                nova_chave_ramo = "outros"
                for k, v in ramos_dict.items():
                    if v == novo_ramo_ui:
                        nova_chave_ramo = k
                        break

                if atualizar_perfil(st.session_state['username'], novo_nome, novo_endereco, nova_senha, foto_blob, nova_chave_ramo, remover_foto_check):
                    st.success(t['profile_success'])
                    st.rerun()
                else:
                    st.error(t['profile_error'])
