import streamlit as st
import pandas as pd
from supabase import create_client, Client
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
    global supabase
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)

init_db()

def cadastrar_usuario(username, nome_completo, senha, ramo_atividade="Outros"):
    dados = {
        "username": username,
        "nome_completo": nome_completo,
        "senha": make_hash(senha),
        "ramo_atividade": ramo_atividade
    }
    supabase.table("usuarios").insert(dados).execute()
    return True

def autenticar_usuario(username, senha):
    try:
        response = supabase.table("usuarios").select("senha").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            senha_cadastrada = response.data[0]["senha"]
            return check_hash(senha, senha_cadastrada)
        return False
    except Exception as e:
        return False

def obter_dados_usuario(username):
    try:
        response = supabase.table("usuarios").select("nome_completo, endereco, foto_perfil, ramo_atividade").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            return (user.get("nome_completo"), user.get("endereco"), user.get("foto_perfil"), user.get("ramo_atividade"))
        return None
    except Exception as e:
        return None

def atualizar_perfil(username, novo_nome, novo_endereco, nova_senha, nova_foto_blob, novo_ramo, remover_foto=False):
    try:
        dados_atualizados = {
            "nome_completo": novo_nome,
            "endereco": novo_endereco,
            "ramo_atividade": novo_ramo
        }
        
        if remover_foto:
            dados_atualizados["foto_perfil"] = None
        elif nova_foto_blob is not None:
            dados_atualizados["foto_perfil"] = nova_foto_blob
            
        if nova_senha:
            dados_atualizados["senha"] = make_hash(nova_senha)
            
        supabase.table("usuarios").update(dados_atualizados).eq("username", username).execute()
        return True
    except Exception as e:
        return False

def carregar_dados(username):
    try:
        response = supabase.table("lancamentos").select("*").eq("username", username).execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def salvar_lancamento(username, data, descricao, categoria, tipo, valor, veiculo=""):
    try:
        dados = {
            "username": username,
            "data": str(data),
            "descricao": descricao,
            "categoria": categoria,
            "tipo": tipo,
            "valor": float(valor),
            "veiculo": veiculo
        }
        supabase.table("lancamentos").insert(dados).execute()
        return True
    except Exception as e:
        return False

def deletar_lancamento(id_lancamento, username):
    try:
        supabase.table("lancamentos").delete().eq("id", id_lancamento).eq("username", username).execute()
        return True
    except Exception as e:
        return False

CATEGORIAS_CHAVES = {
    "mecanica": {
        "desp": ["pecas_insumos", "ferramentas", "equipamentos", "manutencao_predial", "aluguel", "impostos_taxas", "outras_despesas"],
        "rec": ["pagamento_clientes", "servicos_realizados", "venda_pecas", "orcamentos_aprovados", "salario", "outras_receitas"]
    },
    "obras": {
        "desp": ["materiais_construcao", "ferramentas", "equipamentos", "mao_de_obra", "combustivel_frete", "outras_despesas"],
        "rec": ["medicao_obra", "pagamento_clientes", "adiantamento_sinal", "venda_sobras", "salario", "outras_receitas"]
    },
    "ti": {
        "desp": ["softwares_assinaturas", "hospedagem_servidores", "equipamentos", "marketing", "cursos_capacitacao", "outras_despesas"],
        "rec": ["desenvolvimento_projetos", "consultoria", "suporte_mensal", "salario", "outras_receitas"]
    },
    "comercio": {
        "desp": ["aquisicao_mercadorias", "embalagens", "frete_logistica", "marketing_anuncios", "aluguel", "outras_despesas"],
        "rec": ["vendas_vista", "vendas_cartao_pix", "vendas_parceladas", "salario", "outras_receitas"]
    },
    "outros": {
        "desp": ["aluguel_prestacao_casa", "agua_gas_energia", "impostos_taxas_geral", "investimentos_reservas", "transportes_combustivel", "alimentacao_supermercado", "saude_farmacia", "lazer_outras_despesas"],
        "rec": ["salario_base", "receitas_variaveis", "investimentos_rendimentos", "outros_ganhos"]
    }
}

TRADUCOES_RAMOS = {
    "Português": {
        "mecanica": "🛠️ Mecânica / Oficina",
        "obras": "🏗️ Obras / Construção",
        "ti": "💻 TI / Desenvolvimento",
        "comercio": "🛍️ Comércio / Loja",
        "outros": "📋 Outros / Pessoal",
        "tipo_despesa": "Despesa",
        "tipo_receita": "Receita",
        "cat_nomes": {
            "pecas_insumos": "Peças / Insumos", "ferramentas": "Ferramentas", "equipamentos": "Equipamentos", "manutencao_predial": "Manutenção Predial", "aluguel": "Aluguel", "impostos_taxas": "Impostos / Taxas", "outras_despesas": "Outras Despesas",
            "pagamento_clientes": "Pagamento de Clientes", "servicos_realizados": "Serviços Realizados", "venda_pecas": "Venda de Peças", "orcamentos_aprovados": "Orçamentos Aprovados", "salario": "Salário", "outras_receitas": "Outras Receitas",
            "materiais_construcao": "Materiais de Construção", "mao_de_obra": "Mão de Obra / Subcontratados", "combustivel_frete": "Combustível / Frete",
            "medicao_obra": "Medição de Obra", "adiantamento_sinal": "Adiantamento / Sinal", "venda_sobras": "Venda de Sobras",
            "softwares_assinaturas": "Softwares / Assinaturas", "hospedagem_servidores": "Hospedagem / Servidores", "marketing": "Marketing", "cursos_capacitacao": "Cursos / Capacitação",
            "desenvolvimento_projetos": "Desenvolvimento de Projetos", "consultoria": "Consultoria", "suporte_mensal": "Suporte Mensal (Retainer)",
            "aquisicao_mercadorias": "Aquisição de Mercadorias", "embalagens": "Embalagens", "frete_logistica": "Frete / Logística", "marketing_anuncios": "Marketing / Anúncios", "vendas_vista": "Vendas à Vista", "vendas_cartao_pix": "Vendas no Cartão / Pix", "vendas_parceladas": "Vendas Parceladas",
            "aluguel_prestacao_casa": "Aluguel / Prestação da Casa", "agua_gas_energia": "Água, Gás e Energia Elétrica", "impostos_taxas_geral": "Impostos e Taxas (IPTU, IPVA, IR)", "investimentos_reservas": "Investimentos e Reservas", "transportes_combustivel": "Transportes e Combustível", "alimentacao_supermercado": "Alimentação e Supermercado", "saude_farmacia": "Saúde e Farmácia", "lazer_outras_despesas": "Lazer e Outras Despesas",
            "salario_base": "Salário Base", "receitas_variaveis": "Receitas Variáveis (Diárias / Bicos)", "investimentos_rendimentos": "Investimentos e Rendimentos", "outros_ganhos": "Outros Ganhos / Outras Receitas"
        }
    },
    "English": {
        "mecanica": "🛠️ Mechanics / Workshop",
        "obras": "🏗️ Construction / Building",
        "ti": "💻 IT / Development",
        "comercio": "🛍️ Retail / Store",
        "outros": "📋 Others / Personal",
        "tipo_despesa": "Expense",
        "tipo_receita": "Income",
        "cat_nomes": {
            "pecas_insumos": "Parts / Supplies", "ferramentas": "Tools", "equipamentos": "Equipment", "manutencao_predial": "Building Maintenance", "aluguel": "Rent", "impostos_taxas": "Taxes / Fees", "outras_despesas": "Other Expenses",
            "pagamento_clientes": "Client Payments", "servicos_realizados": "Services Rendered", "venda_pecas": "Parts Sales", "orcamentos_aprovados": "Approved Budgets", "salario": "Salary", "outras_receitas": "Other Income",
            "materiais_construcao": "Building Materials", "mao_de_obra": "Labor / Subcontractors", "combustivel_frete": "Fuel / Freight",
            "medicao_obra": "Construction Measurement", "adiantamento_sinal": "Advance / Deposit", "venda_sobras": "Surplus Sales",
            "softwares_assinaturas": "Software / Subscriptions", "hospedagem_servidores": "Hosting / Servers", "marketing": "Marketing", "cursos_capacitacao": "Courses / Training",
            "desenvolvimento_projetos": "Project Development", "consultoria": "Consulting", "suporte_mensal": "Monthly Support (Retainer)",
            "aquisicao_mercadorias": "Goods Acquisition", "embalagens": "Packaging", "frete_logistica": "Freight / Logistics", "marketing_anuncios": "Marketing / Ads", "vendas_vista": "Cash Sales", "vendas_cartao_pix": "Card / Pix Sales", "vendas_parceladas": "Installment Sales",
            "aluguel_prestacao_casa": "Rent / House Installment", "agua_gas_energia": "Water, Gas & Electricity", "impostos_taxas_geral": "Taxes & Fees", "investimentos_reservas": "Investments & Reserves", "transportes_combustivel": "Transport & Fuel", "alimentacao_supermercado": "Groceries & Food", "saude_farmacia": "Health & Pharmacy", "lazer_outras_despesas": "Leisure & Other Expenses",
            "salario_base": "Base Salary", "receitas_variaveis": "Variable Income (Daily work / Extras)", "investimentos_rendimentos": "Investments & Yields", "outros_ganhos": "Other Earnings"
        }
    },
    "Français": {
        "mecanica": "🛠️ Mécanique / Atelier",
        "obras": "🏗️ Bâtiment / Construction",
        "ti": "💻 Informatique / Développement",
        "comercio": "🛍️ Commerce / Magasin",
        "outros": "📋 Autres / Personnel",
        "tipo_despesa": "Dépense",
        "tipo_receita": "Revenu",
        "cat_nomes": {
            "pecas_insumos": "Pièces / Consommables", "ferramentas": "Outils", "equipamentos": "Équipement", "manutencao_predial": "Maintenance des Locaux", "aluguel": "Loyer", "impostos_taxas": "Impôts / Taxes", "outras_despesas": "Autres Dépenses",
            "pagamento_clientes": "Paiement des Clients", "servicos_realizados": "Services Réalisés", "venda_pecas": "Vente de Pièces", "orcamentos_aprovados": "Devis Approuvés", "salario": "Salaire", "outras_receitas": "Autres Revenus",
            "materiais_construcao": "Matériaux de Construction", "mao_de_obra": "Main-d'œuvre / Sous-traitants", "combustivel_frete": "Carburant / Fret",
            "medicao_obra": "Mesurage de Chantier", "adiantamento_sinal": "Acompte / Avance", "venda_sobras": "Vente de Surplus",
            "softwares_assinaturas": "Logiciels / Abonnements", "hospedagem_servidores": "Hébergement / Serveurs", "marketing": "Marketing", "cursos_capacitacao": "Formations",
            "desenvolvimento_projetos": "Développement de Projets", "consultoria": "Conseil", "suporte_mensal": "Support Mensuel (Retainer)",
            "aquisicao_mercadorias": "Achat de Marchandises", "embalagens": "Emballages", "frete_logistica": "Fret / Logistique", "marketing_anuncios": "Marketing / Publicité",
            "aluguel_prestacao_casa": "Loyer / Prêt Immobilier", "agua_gas_energia": "Eau, Gaz et Électricité", "impostos_taxas_geral": "Impôts et Taxes", "investimentos_reservas": "Investissements et Réserves", "transportes_combustivel": "Transport et Carburant", "alimentacao_supermercado": "Alimentation et Supermarché", "saude_farmacia": "Santé et Pharmacie", "lazer_outras_despesas": "Loisirs et Autres Dépenses",
            "salario_base": "Salaire de Base", "receitas_variaveis": "Revenus Variables (Journées / Extras)", "investimentos_rendimentos": "Investissements et Rendements", "outros_ganhos": "Autres Gains"
        }
    },
    "Español": {
        "mecanica": "🛠️ Mecánica / Taller",
        "obras": "🏗️ Obras / Construcción",
        "ti": "💻 TI / Desarrollo",
        "comercio": "🛍️ Comercio / Tienda",
        "outros": "📋 Otros / Personal",
        "tipo_despesa": "Gasto",
        "tipo_receita": "Ingreso",
        "cat_nomes": {
            "pecas_insumos": "Piezas / Insumos", "ferramentas": "Herramientas", "equipamentos": "Equipos", "manutencao_predial": "Mantenimiento", "aluguel": "Alquiler", "impostos_taxas": "Impuestos / Tasas", "outras_despesas": "Otros Gastos",
            "pagamento_clientes": "Pago de Clientes", "servicos_realizados": "Servicios Realizados", "venda_pecas": "Venta de Piezas", "orcamentos_aprovados": "Presupuestos Aprobados", "salario": "Salario", "outras_receitas": "Otros Ingresos",
            "materiais_construcao": "Materiales de Construcción", "mao_de_obra": "Mano de Obra / Subcontratados", "combustivel_frete": "Combustible / Flete",
            "medicao_obra": "Medición de Obra", "adiantamento_sinal": "Anticipo / Seña", "venda_sobras": "Venta de Sobrantes",
            "softwares_assinaturas": "Software / Suscripciones", "hospedagem_servidores": "Hosting / Servidores", "marketing": "Marketing", "cursos_capacitacao": "Cursos / Capacitación",
            "desenvolvimento_projetos": "Desarrollo de Proyectos", "consultoria": "Consultoría", "suporte_mensal": "Soporte Mensual",
            "aquisicao_mercadorias": "Adquisición de Mercancías", "embalagens": "Embalajes", "frete_logistica": "Flete / Logística", "marketing_anuncios": "Marketing / Anuncios", "vendas_vista": "Ventas al Contado", "vendas_cartao_pix": "Ventas con Tarjeta / Pix", "vendas_parceladas": "Ventas en Cuotas",
            "aluguel_prestacao_casa": "Alquiler / Cuota de Casa", "agua_gas_energia": "Agua, Gas y Electricidad", "impostos_taxas_geral": "Impuestos y Tasas", "investimentos_reservas": "Inversiones y Reservas", "transportes_combustivel": "Transporte y Combustible", "alimentacao_supermercado": "Alimentación y Supermercado", "saude_farmacia": "Salud y Farmacia", "lazer_outras_despesas": "Ocio y Otros Gastos",
            "salario_base": "Salario Base", "receitas_variaveis": "Ingresos Variables (Diarias / Extras)", "investimentos_rendimentos": "Inversiones y Rendimientos", "outros_ganhos": "Otros Ingresos"
        }
    },
    "Italiano": {
        "mecanica": "🛠️ Meccanica / Officina",
        "obras": "🏗️ Edilizia / Costruzione",
        "ti": "💻 IT / Sviluppo",
        "comercio": "🛍️ Commercio / Negozio",
        "outros": "📋 Altro / Personale",
        "tipo_despesa": "Spesa",
        "tipo_receita": "Entrata",
        "cat_nomes": {
            "pecas_insumos": "Ricambi / Materiali", "ferramentas": "Utensili", "equipamentos": "Attrezzatura", "manutencao_predial": "Manutenzione", "aluguel": "Affitto", "impostos_taxas": "Tasse / Imposte", "outras_despesas": "Altre Spese",
            "pagamento_clientes": "Pagamenti Clienti", "servicos_realizados": "Servizi Eseguiti", "venda_pecas": "Vendita Ricambi", "orcamentos_aprovados": "Preventivi Approvati", "salario": "Stipendio", "outras_receitas": "Altre Entrate",
            "materiais_construcao": "Materiali Edili", "mao_de_obra": "Manodopera / Subappalti", "combustivel_frete": "Carburante / Trasporto",
            "medicao_obra": "Stato Avanzamento Lavori", "adiantamento_sinal": "Acconto", "venda_sobras": "Vendita Surplus",
            "softwares_assinaturas": "Software / Abbonamenti", "hospedagem_servidores": "Hosting / Server", "marketing": "Marketing", "cursos_capacitacao": "Corsi / Formazione",
            "desenvolvimento_projetos": "Sviluppo Progetti", "consultoria": "Consulenza", "suporte_mensal": "Supporto Mensile",
            "aquisicao_mercadorias": "Acquisto Merce", "embalagens": "Imballaggi", "frete_logistica": "Spedizione / Logistica", "marketing_anuncios": "Marketing / Annunci", "vendas_vista": "Vendite in Contanti", "vendas_cartao_pix": "Vendite Carta / Pix", "vendas_parceladas": "Vendite Rateali",
            "aluguel_prestacao_casa": "Affitto / Mutuo Casa", "agua_gas_energia": "Acqua, Gas ed Elettricità", "impostos_taxas_geral": "Tasse e Imposte", "investimentos_reservas": "Investimenti e Riserve", "transportes_combustivel": "Trasporti e Carburante", "alimentacao_supermercado": "Spesa Alimentare", "saude_farmacia": "Salute e Farmacia", "lazer_outras_despesas": "Tempo Libero e Altre Spese",
            "salario_base": "Stipendio Base", "receitas_variaveis": "Entrate Variabili (Giornate / Extra)", "investimentos_rendimentos": "Investimenti e Rendimenti", "outros_ganhos": "Altri Guadagni"
        }
    },
    "Deutsch": {
        "mecanica": "🛠️ Mechanik / Werkstatt",
        "obras": "🏗️ Bauwesen / Konstruktion",
        "ti": "💻 IT / Entwicklung",
        "comercio": "🛍️ Handel / Geschäft",
        "outros": "📋 Sonstiges / Persönlich",
        "tipo_despesa": "Ausgabe",
        "tipo_receita": "Einnahme",
        "cat_nomes": {
            "pecas_insumos": "Teile / Verbrauchsmaterial", "ferramentas": "Werkzeuge", "equipamentos": "Ausstattung", "manutencao_predial": "Gebäudewartung", "aluguel": "Miete", "impostos_taxas": "Steuern / Gebühren", "outras_despesas": "Sonstige Ausgaben",
            "pagamento_clientes": "Kundenzahlungen", "servicos_realizados": "Erbrachte Dienstleistungen", "venda_pecas": "Teileverkauf", "orcamentos_aprovados": "Genehmigte Budgets", "salario": "Gehalt", "outras_receitas": "Sonstige Einnahmen",
            "materiais_construcao": "Baumaterialien", "mao_de_obra": "Arbeitskräfte / Subunternehmer", "combustivel_frete": "Kraftstoff / Fracht",
            "medicao_obra": "Bauabrechnung", "adiantamento_sinal": "Vorschuss / Anzahlung", "venda_sobras": "Restverkauf",
            "softwares_assinaturas": "Software / Abonnements", "hospedagem_servidores": "Hosting / Server", "marketing": "Marketing", "cursos_capacitacao": "Kurse / Schulungen",
            "desenvolvimento_projetos": "Projektentwicklung", "consultoria": "Beratung", "suporte_mensal": "Monatlicher Support",
            "aquisicao_mercadorias": "Warenerwerb", "embalagens": "Verpackung", "frete_logistica": "Fracht / Logistik", "marketing_anuncios": "Marketing / Werbung", "vendas_vista": "Barverkäufe", "vendas_cartao_pix": "Kartenzahlung / Pix", "vendas_parceladas": "Ratenverkäufe",
            "aluguel_prestacao_casa": "Miete / Hauskredit", "agua_gas_energia": "Wasser, Gas und Strom", "impostos_taxas_geral": "Steuern und Gebühren", "investimentos_reservas": "Investitionen und Rücklagen", "transportes_combustivel": "Transport und Kraftstoff", "alimentacao_supermercado": "Lebensmittel und Supermarkt", "saude_farmacia": "Gesundheit und Apotheke", "lazer_outras_despesas": "Freizeit und Sonstige Ausgaben",
            "salario_base": "Grundgehalt", "receitas_variaveis": "Variables Einkommen (Tagelöhner / Extras)", "investimentos_rendimentos": "Investitionen und Renditen", "outros_ganhos": "Sonstige Einnahmen"
        }
    }
}

TEXTOS = {
    "Português": {
        "login_title": "Acesso ao Meu Financeiro",
        "login_sub": "Entre com sua conta ou cadastre-se escolhendo o seu perfil.",
        "tab_login": "🔑 Entrar",
        "tab_register_pessoal": "👤 Perfil Pessoal",
        "tab_register_prof": "🛠️ Perfil Profissional",
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
        "veiculo_label": "Veículo / Frota / Placa (Opcional)",
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
        "highest_costs": "Maiores Costos por Categoria",
        "biz_report": "📋 Relatório Analítico de Lançamentos do Negócio",
        "id_del_label": "ID do lançamento para excluir",
        "del_success": "Lançamento excluído com sucesso!",
        "info_pessoal": "Criação de conta estritamente pessoal (sem exigência de ramo profissional ou oficina).",
        "info_prof": "Criação de conta profissional voltada para o seu setor de mercado."
    },
    "English": {
        "login_title": "My Finance Access",
        "login_sub": "Log in to your account or choose your profile type to register.",
        "tab_login": "🔑 Log In",
        "tab_register_pessoal": "👤 Personal Profile",
        "tab_register_prof": "🛠️ Professional Profile",
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
        "veiculo_label": "Vehicle / Fleet / Plate (Optional)",
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
        "del_success": "Entry deleted successfully!",
        "info_pessoal": "Strictly personal account creation (no professional or workshop branch required).",
        "info_prof": "Professional account creation tailored to your market sector."
    },
    "Français": {
        "login_title": "Accès à Mon Financier",
        "login_sub": "Connectez-vous ou choisissez votre profil pour vous inscrire.",
        "tab_login": "🔑 Connexion",
        "tab_register_pessoal": "👤 Profil Personnel",
        "tab_register_prof": "🛠️ Profil Professionnel",
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
        "veiculo_label": "Véhicule / Flotte / Plaque (Optionnel)",
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
        "del_success": "Entrée supprimée avec succès !",
        "info_pessoal": "Création de compte strictement personnel (sans exigence de secteur professionnel ou d'atelier).",
        "info_prof": "Création de compte professionnel adapté à votre secteur de marché."
    },
    "Español": {
        "login_title": "Acceso a Mi Financiero",
        "login_sub": "Inicia sesión o regístrese seleccionando su perfil.",
        "tab_login": "🔑 Entrar",
        "tab_register_pessoal": "👤 Perfil Personal",
        "tab_register_prof": "🛠️ Perfil Profesional",
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
        "reg_error": "Este usuario ya existe ou hubo un error.",
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
        "veiculo_label": "Vehículo / Flota / Patente (Opcional)",
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
        "del_success": "¡Movimiento eliminado con éxito!",
        "info_pessoal": "Creación de cuenta estrictamente personal (sin requerir sector profesional o taller).",
        "info_prof": "Creación de cuenta profesional adaptada a tu sector de mercado."
    },
    "Italiano": {
        "login_title": "Accesso a Il Mio Finanziario",
        "login_sub": "Accedi al tuo account o registrati scegliendo il profilo.",
        "tab_login": "🔑 Accedi",
        "tab_register_pessoal": "👤 Profilo Personale",
        "tab_register_prof": "🛠️ Profilo Professionale",
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
        "veiculo_label": "Veicolo / Flotta / Targa (Opzionale)",
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
        "del_success": "Voce eliminata con successo!",
        "info_pessoal": "Creazione account strettamente personale (senza requisiti di settore professionale o officina).",
        "info_prof": "Creazione account professionale su misura per il tuo settore di mercato."
    },
    "Deutsch": {
        "login_title": "Mein Finanz-Zugang",
        "login_sub": "Melden Sie sich an oder wählen Sie Ihr Profil zur Registrierung.",
        "tab_login": "🔑 Anmelden",
        "tab_register_pessoal": "👤 Persönliches Profil",
        "tab_register_prof": "🛠️ Professionelles Profil",
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
        "veiculo_label": "Fahrzeug / Flotte / Kennzeichen (Optional)",
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
        "del_success": "Eintrag erfolgreich gelöscht!",
        "info_pessoal": "Streng persönliches Konto (kein Berufszweig oder Werkstatt erforderlich).",
        "info_prof": "Professionelles Konto zugeschnitten auf Ihre Branche."
    }
}

MOEDAS = {
    "Real (R$)": "R$",
    "Euro (€)": "€",
    "Dólar ($)": "$",
    "Libra (£)": "£"
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
        
        tab_login, tab_reg_pessoal, tab_reg_prof = st.tabs([
            t_login['tab_login'], 
            t_login['tab_register_pessoal'], 
            t_login['tab_register_prof']
        ])
        
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
                        
        with tab_reg_pessoal:
            with st.form("form_reg_pessoal"):
                st.info(t_login['info_pessoal'])
                reg_user_p = st.text_input(t_login['reg_user_label'], key="reg_u_p")
                reg_name_p = st.text_input(t_login['reg_name_label'], key="reg_n_p")
                reg_pass_p = st.text_input(t_login['reg_pass_label'], type="password", key="reg_p_p")
                
                submit_reg_p = st.form_submit_button(t_login['btn_reg_submit'], use_container_width=True)
                
                if submit_reg_p:
                    if reg_user_p and reg_name_p and reg_pass_p:
                        if cadastrar_usuario(reg_user_p, reg_name_p, reg_pass_p, "outros"):
                            st.success(t_login['reg_success'])
                        else:
                            st.error(t_login['reg_error'])
                    else:
                        st.warning(t_login['reg_warn'])

        with tab_reg_prof:
            with st.form("form_reg_prof"):
                st.info(t_login['info_prof'])
                reg_user_prof = st.text_input(t_login['reg_user_label'], key="reg_u_prof")
                reg_name_prof = st.text_input(t_login['reg_name_label'], key="reg_n_prof")
                reg_pass_prof = st.text_input(t_login['reg_pass_label'], type="password", key="reg_p_prof")
                
                opcoes_ramos_reg = [
                    ramos_atuais_dict["mecanica"],
                    ramos_atuais_dict["obras"],
                    ramos_atuais_dict["ti"],
                    ramos_atuais_dict["comercio"]
                ]
                reg_branch_ui = st.selectbox(t_login['reg_branch_label'], opcoes_ramos_reg, key="reg_branch_prof")
                
                submit_reg_prof = st.form_submit_button(t_login['btn_reg_submit'], use_container_width=True)
                
                if submit_reg_prof:
                    if reg_user_prof and reg_name_prof and reg_pass_prof:
                        chave_ramo = "outros"
                        for k, v in ramos_atuais_dict.items():
                            if v == reg_branch_ui:
                                chave_ramo = k
                                break
                        if cadastrar_usuario(reg_user_prof, reg_name_prof, reg_pass_prof, chave_ramo):
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

        sel_lang = st.selectbox(t['lang_label'], lista_idiomas, index=lista_idiomas.index(st.session_state['idioma']), key="sb_lang")
        if sel_lang != st.session_state['idioma']:
            st.session_state['idioma'] = sel_lang
            st.rerun()

        sel_moeda = st.selectbox(t['curr_label'], list(MOEDAS.keys()), index=list(MOEDAS.keys()).index(st.session_state['moeda']), key="sb_curr")
        if sel_moeda != st.session_state['moeda']:
            st.session_state['moeda'] = sel_moeda
            st.rerun()

        st.markdown("---")
        
        if ramo_usuario_db == "outros":
            opcoes_menu = [
                t['nav_overview'],
                t['nav_new'],
                t['nav_manage'],
                t['nav_profile']
            ]
        else:
            opcoes_menu = [
                t['nav_overview'],
                t['nav_business'],
                t['nav_new'],
                t['nav_manage'],
                t['nav_profile']
            ]

        menu = st.radio("Navegação", opcoes_menu)

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button(t['logout'], use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ""
            st.rerun()

    df = carregar_dados(st.session_state['username'])

    def traduzir_categoria(cat_salva):
        if not cat_salva:
            return ""
        if cat_salva in ramos_dict["cat_nomes"]:
            return ramos_dict["cat_nomes"][cat_salva]
        for lang_key, lang_data in TRADUCOES_RAMOS.items():
            for c_key, c_val in lang_data["cat_nomes"].items():
                if c_val.lower() == str(cat_salva).lower():
                    return ramos_dict["cat_nomes"].get(c_key, cat_salva)
        return cat_salva

    def traduzir_tipo(tipo_salvo):
        if not tipo_salvo:
            return ""
        if tipo_salvo in ["Despesa", "Expense", "Dépense", "Gasto", "Spesa", "Ausgabe"]:
            return ramos_dict["tipo_despesa"]
        if tipo_salvo in ["Receita", "Income", "Revenu", "Ingreso", "Entrata", "Einnahme"]:
            return ramos_dict["tipo_receita"]
        return tipo_salvo

    if not df.empty:
        df["categoria_exibicao"] = df["categoria"].apply(traduzir_categoria)
        df["tipo_exibicao"] = df["tipo"].apply(traduzir_tipo)

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

            total_receitas = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_receita"]]['valor'].sum()
            total_despesas = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_despesa"]]['valor'].sum()
            
            df_inv_mes = df_mes[df_mes['categoria'].str.contains("investimento|reserva", case=False, na=False)]
            investimento_mes = df_inv_mes['valor'].sum() if not df_inv_mes.empty else 0.0

            saldo_mes = total_receitas - total_despesas

            df_historico = df[df["mes_ano"] <= mes_selecionado]
            hist_rec = df_historico[df_historico['tipo_exibicao'] == ramos_dict["tipo_receita"]]['valor'].sum()
            hist_esp = df_historico[df_historico['tipo_exibicao'] == ramos_dict["tipo_despesa"]]['valor'].sum()
            saldo_real_conta = hist_rec - hist_esp

            df_inv_total = df[df['categoria'].str.contains("investimento|reserva", case=False, na=False)]
            investimento_total = df_inv_total['valor'].sum() if not df_inv_total.empty else 0.0

            # Organizado em 2 colunas (Coluna A e Coluna B) conforme solicitado
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(t['total_rev'], f"{simbolo_moeda} {total_receitas:,.2f}")
                st.metric(t['total_exp'], f"{simbolo_moeda} {total_despesas:,.2f}")
                st.metric("⚡ Saldo do Mês", f"{simbolo_moeda} {saldo_mes:,.2f}")
                
            with col2:
                st.metric("📈 Investimento do Mês", f"{simbolo_moeda} {investimento_mes:,.2f}")
                st.metric("💎 Total Investido (Acumulado)", f"{simbolo_moeda} {investimento_total:,.2f}")
                st.metric("🏦 Saldo Real na Conta (Acumulado)", f"{simbolo_moeda} {saldo_real_conta:,.2f}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                df_desp = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_despesa"]]
                if not df_desp.empty:
                    fig_pie = px.pie(df_desp, names='categoria_exibicao', values='valor', title=t['pie_title'], hole=0.4)
                    fig_pie.update_layout(dragmode=False)
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
                else:
                    st.info("Sem despesas para exibir no gráfico neste mês.")

            with c2:
                if not df_mes.empty:
                    fig_bar = px.bar(df_mes, x='data', y='valor', color='tipo_exibicao', title=t['bar_title'], barmode='group')
                    fig_bar.update_layout(dragmode=False, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
                else:
                    st.info("Sem dados para o gráfico.")

            st.subheader(t['recent_list'])
            df_exibicao_tabela = df_mes[['data', 'tipo_exibicao', 'categoria_exibicao', 'descricao', 'valor']].copy()
            df_exibicao_tabela.columns = ['Data', 'Tipo', 'Categoria', 'Descrição', 'Valor']
            st.dataframe(df_exibicao_tabela, use_container_width=True)

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

            faturamento = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_receita"]]['valor'].sum()
            custos = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_despesa"]]['valor'].sum()
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
                df_rec = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_receita"]]
                if not df_rec.empty:
                    fig_rec = px.pie(df_rec, names='categoria_exibicao', values='valor', title=t['origin_rev'], hole=0.4)
                    fig_rec.update_layout(dragmode=False)
                    st.plotly_chart(fig_rec, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
                else:
                    st.info("Nenhuma receita registrada neste mês.")

            with bc2:
                st.subheader(t['op_costs_biz'])
                df_desp = df_mes[df_mes['tipo_exibicao'] == ramos_dict["tipo_despesa"]]
                if not df_desp.empty:
                    fig_desp = px.bar(df_desp, x='categoria_exibicao', y='valor', title=t['highest_costs'], color='categoria_exibicao')
                    fig_desp.update_layout(dragmode=False, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
                    st.plotly_chart(fig_desp, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
                else:
                    st.info("Nenhuma despesa registrada neste mês.")

            st.subheader(t['biz_report'])
            colunas_relatorio = ['data', 'tipo_exibicao', 'categoria_exibicao', 'descricao', 'veiculo', 'valor'] if 'veiculo' in df_mes.columns else ['data', 'tipo_exibicao', 'categoria_exibicao', 'descricao', 'valor']
            df_biz_tab = df_mes[[c for c in colunas_relatorio if c in df_mes.columns]].copy()
            df_biz_tab.columns = ['Data', 'Tipo', 'Categoria', 'Descrição', 'Veículo', 'Valor'] if 'veiculo' in colunas_relatorio else ['Data', 'Tipo', 'Categoria', 'Descrição', 'Valor']
            st.dataframe(df_biz_tab, use_container_width=True)

    elif menu == t['nav_new']:
        st.title(t['new_title'])
        st.write(t['new_sub'])

        ramo_chave_atual = ramo_usuario_db if ramo_usuario_db in CATEGORIAS_CHAVES else "outros"
        chaves_desp = CATEGORIAS_CHAVES[ramo_chave_atual]["desp"]
        chaves_rec = CATEGORIAS_CHAVES[ramo_chave_atual]["rec"]

        data_lanc = st.date_input(t['date_label'], datetime.date.today())
        
        tipo_opcoes_ui = [ramos_dict["tipo_despesa"], ramos_dict["tipo_receita"]]
        tipo_lanc_ui = st.selectbox(t['type_label'], tipo_opcoes_ui)
        
        valor_lanc = st.number_input(f"{t['value_label']} ({simbolo_moeda})", min_value=0.0, format="%.2f")
        
        if tipo_lanc_ui == ramos_dict["tipo_receita"]:
            lista_chaves = chaves_rec
        else:
            lista_chaves = chaves_desp
            
        opcoes_cat_ui = [ramos_dict["cat_nomes"][k] for k in lista_chaves]
        cat_escolhida_ui = st.selectbox(t['cat_label'], opcoes_cat_ui)
        
        cat_lanc_chave = lista_chaves[0]
        for k in lista_chaves:
            if ramos_dict["cat_nomes"][k] == cat_escolhida_ui:
                cat_lanc_chave = k
                break
        
        desc_lanc = st.text_input(t['desc_label'])
        
        veiculo_lanc = ""
        if ramo_usuario_db == "mecanica":
            veiculo_lanc = st.text_input(t['veiculo_label'])
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t['save_btn'], use_container_width=True):
            if desc_lanc.strip() != "":
                tipo_para_salvar = "Despesa" if tipo_lanc_ui == ramos_dict["tipo_despesa"] else "Receita"
                sucesso = salvar_lancamento(
                    st.session_state['username'], 
                    str(data_lanc), 
                    desc_lanc, 
                    cat_lanc_chave, 
                    tipo_para_salvar, 
                    float(valor_lanc), 
                    veiculo_lanc
                )
                if sucesso:
                    st.success(t['success_msg'])
                    st.rerun()
                else:
                    st.error("Erro ao salvar no banco de dados.")
            else:
                st.warning(t['warn_desc'])

    elif menu == t['nav_manage']:
        st.title(t['manage_title'])
        st.write(t['manage_sub'])

        if df.empty:
            st.info(t['no_data'])
        else:
            df_gerenciar = df[['id', 'data', 'tipo_exibicao', 'categoria_exibicao', 'descricao', 'valor']].copy()
            df_gerenciar.columns = ['ID', 'Data', 'Tipo', 'Categoria', 'Descrição', 'Valor']
            st.dataframe(df_gerenciar, use_container_width=True)
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
