def obter_token():
    ip_limpo = limpar_ip(IMASTER_IP)
    PORTA_API = "18002" # Porta padrão comum
    
    # Lista de todas as rotas possíveis de autenticação da Huawei
    rotas_para_testar = [
        f"https://{ip_limpo}:{PORTA_API}/v1/auth/tokens",                      # Rota 1: Campus Padrão
        f"https://{ip_limpo}:18008/rest/plat/v1/auth/tokens",                  # Rota 2: WAN / IP Core
        f"https://{ip_limpo}:{PORTA_API}/rest/plat/v1/auth/tokens"             # Rota 3: WAN Alternativa
    ]
    
    requests.packages.urllib3.disable_warnings() 
    
    # O loop vai testar uma por uma automaticamente
    for url in rotas_para_testar:
        try:
            response = requests.post(
                url, 
                json={"userName": USERNAME, "password": PASSWORD}, 
                headers={"Content-Type": "application/json"}, 
                verify=False, 
                timeout=4
            )
            
            # Se encontrar a rota certa (Status 200 ou 201), captura o Token
            if response.status_code in [200, 201]:
                st.success(f"🔗 Conectado com sucesso via rota: {url}")
                return response.json()['data']['token_id']
                
        except Exception:
            continue # Se der erro de timeout ou rede nesta rota, pula para a próxima
            
    # Se sair do loop e não encontrar nenhuma rota funcional:
    st.error("❌ Todas as rotas de API retornaram erro (404 ou Timeout). Verifique se o IP/Portas estão liberados no Firewall ou consulte o modelo exato do seu iMaster.")
    return None
