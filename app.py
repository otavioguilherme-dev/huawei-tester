import streamlit as st
import requests

# --- 1. VALIDAÇÃO DOS SECRETS ---
try:
    IMASTER_IP = st.secrets["IMASTER_IP"]
    USERNAME = st.secrets["USERNAME"]
    PASSWORD = st.secrets["PASSWORD"]
    config_ok = True
except Exception:
    config_ok = False

def limpar_ip(ip):
    if not ip:
        return ""
    return ip.replace("https://", "").replace("http://", "").strip("/")

# --- 2. FUNÇÕES DE API (PADRÃO WAN CORE) ---
def obter_token():
    ip_limpo = limpar_ip(IMASTER_IP)
    
    # Lista atualizada com as URLs de OpenAPI e RESTCONF do iMaster NCE mais recente
    combinacoes = [
        # 1. Nova rota unificada OpenAPI (Comum nas versões recentes na porta 18008)
        {"url": f"https://{ip_limpo}:18008/rest/openapi/v1/auth/tokens", "tipo": "openapi"},
        
        # 2. Rota Legada WAN/IP
        {"url": f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens", "tipo": "wan_estrito"},
        
        # 3. Rota Legada Campus
        {"url": f"https://{ip_limpo}:18002/v1/auth/tokens", "tipo": "campus"}
    ]
    
    requests.packages.urllib3.disable_warnings() 
    
    for item in combinacoes:
        url = item["url"]
        
        # Ajusta o JSON dependendo do padrão da rota
        if item["tipo"] == "wan_estrito":
            payload = {"authParams": {"userName": USERNAME, "password": PASSWORD}}
        elif item["tipo"] == "openapi":
            # Algumas versões utilizam chaves planas, outras estruturadas
            payload = {"userName": USERNAME, "password": PASSWORD}
        else:
            payload = {"userName": USERNAME, "password": PASSWORD}
            
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                verify=False, 
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                dados = response.json()
                # Extração inteligente do Token
                if 'data' in dados and 'token_id' in dados['data']:
                    return dados['data']['token_id']
                elif 'token' in dados:
                    return dados['token']
                elif 'access_token' in dados:
                    return dados['access_token']
                elif 'token_id' in dados:
                    return dados['token_id']
        except Exception:
            continue
            
    return None

@st.cache_data(ttl=300)
def listar_todos_os_elementos(token):
    """Busca os Elementos de Rede (Roteadores/Sites) no padrão NCE-WAN"""
    ip_limpo = limpar_ip(IMASTER_IP)
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    
    # Rota Nativa de Inventário de Roteadores/Dispositivos (NCE-IP)
    url = f"https://{ip_limpo}:18008/rest/netconf-data/v1/network-elements"
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=8)
        if response.status_code == 200:
            dados = response.json().get('network-elements', {}).get('network-element', [])
            # Se a rota acima funcionar, mapeia Nome do Equipamento -> ID do Equipamento
            return {ne['name']: ne['ne-id'] for ne in dados if 'name' in ne}
    except Exception:
        pass
        
    # Rota Alternativa caso a primeira falhe (Campus fallback)
    url_alt = f"https://{ip_limpo}:18008/controller/campus/v1/sdwan/net/sites"
    try:
        response = requests.get(url_alt, headers=headers, verify=False, timeout=8)
        if response.status_code == 200:
            dados = response.json().get('data', [])
            return {site['name']: site['id'] for site in dados if 'name' in site}
    except Exception:
        pass

    return {}

def buscar_alarmes_elemento(ne_id, token):
    """Busca alarmes ativos filtrados pelo ID do elemento selecionado"""
    ip_limpo = limpar_ip(IMASTER_IP)
    headers = {"X-AUTH-TOKEN": token, "Content-Type": "application/json"}
    
    # Rota universal de alarmes ativos
    url = f"https://{ip_limpo}:18008/rest/openapi/fault/v1/active-alarms?neId={ne_id}"
    
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=8)
        if res.status_code == 200:
            return res.json().get('data', []), None
    except Exception:
        pass
        
    # Fallback Campus
    url_alt = f"https://{ip_limpo}:18008/controller/campus/v1/alarms?siteId={ne_id}&status=active"
    try:
        res = requests.get(url_alt, headers=headers, verify=False, timeout=8)
        if res.status_code == 200:
            return res.json().get('data', []), None
    except Exception as e:
        return None, f"Erro ao coletar alarmes: {e}"

# --- 3. INTERFACE GRÁFICA ---
st.set_page_config(page_title="O&M iMaster Huawei", page_icon="🌐")
st.title("🌐 Portal de Troubleshooting Inteligente - Huawei iMaster")

if not config_ok:
    st.error("⚠️ Configuração Incompleta nos Secrets do Streamlit.")
else:
    with st.spinner("Conectando ao barramento de API do iMaster..."):
        token_atual = obter_token()
        if token_atual:
            dicionario_pontos = listar_todos_os_elementos(token_atual)
        else:
            dicionario_pontos = {}

    if dicionario_pontos:
        st.success(f"Sucesso! {len(dicionario_pontos)} localidades/equipamentos mapeados para monitoramento.")
        
        lista_nomes = sorted(list(dicionario_pontos.keys()))
        ponto_selecionado = st.selectbox("Selecione o Ponto/Circuito para Análise:", lista_nomes)
        
        if st.button("Executar Troubleshooting"):
            id_do_ponto = dicionario_pontos[ponto_selecionado]
            
            with st.spinner(f"Verificando integridade física e perdas em {ponto_selecionado}..."):
                alarmes, erro = buscar_alarmes_elemento(id_do_ponto, token_atual)
                
                if erro:
                    st.error(erro)
                elif len(alarmes) == 0:
                    st.success(f"✅ **STATUS: 100% OPERACIONAL**. O ponto {ponto_selecionado} não apresenta perda de pacotes ou quedas registradas.")
                else:
                    st.error(f"❌ **STATUS: ALERTA DE ANOMALIA ({len(alarmes)} falhas detectadas)**")
                    
                    dados_tabela = []
                    for al_item in alarmes:
                        dados_tabela.append({
                            "Gravidade": al_item.get('severity') or al_item.get('perceivedSeverity'),
                            "Falha/Alarme": al_item.get('alarmName') or al_item.get('alarmIdName'),
                            "Objeto Afetado": al_item.get('objectName') or al_item.get('neName'),
                            "Data": al_item.get('startTime') or al_item.get('eventTime')
                        })
                    st.dataframe(dados_tabela, use_container_width=True)
    else:
        if token_atual:
            st.warning("⚠️ Conectado com sucesso, mas o inventário retornou vazio. Verifique se o seu perfil de usuário possui escopo de leitura para a topologia.")
