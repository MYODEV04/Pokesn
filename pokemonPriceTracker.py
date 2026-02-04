import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="포켓몬 카드 가격 검색",
    page_icon="🎴",
    layout="wide"
)

# 제목
st.title("🎴 포켓몬 카드 가격 검색")
st.markdown("Pokemon TCG API를 통해 포켓몬 카드의 시장 가격과 정보를 확인하세요!")

def search_pokemon_cards(query):
    """Pokemon TCG API를 사용하여 카드 검색"""
    try:
        # Pokemon TCG API 엔드포인트
        url = "https://api.pokemontcg.io/v2/cards"
        
        # 여러 검색 방법 시도
        search_attempts = [
            {'q': f'name:"{query}"'},  # 정확한 검색
            {'q': f'name:{query}'},     # 따옴표 없이
            {'q': f'name:*{query}*'},   # 와일드카드
        ]
        
        # 첫 단어만 추출 (Detective Pikachu -> Detective)
        first_word = query.split()[0] if ' ' in query else query
        if first_word != query:
            search_attempts.append({'q': f'name:{first_word}'})
        
        response = None
        for params in search_attempts:
            params['pageSize'] = 20
            try:
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        break  # 성공하면 루프 종료
            except:
                continue
        
        if not response or response.status_code != 200:
            return None, "카드를 찾을 수 없습니다. 포켓몬 이름만 입력해보세요 (예: Pikachu)"
        
        data = response.json()
        
        if 'data' not in data or len(data['data']) == 0:
            return [], None
        
        # 카드 정보 추출
        cards = []
        for card in data['data']:
            card_info = {
                'name': card.get('name', 'Unknown'),
                'set': card.get('set', {}).get('name', 'Unknown Set'),
                'number': card.get('number', 'N/A'),
                'rarity': card.get('rarity', 'N/A'),
                'image': card.get('images', {}).get('large', None),
                'image_small': card.get('images', {}).get('small', None),
                'prices': card.get('cardmarket', {}).get('prices', {}),
                'tcgplayer_prices': card.get('tcgplayer', {}).get('prices', {}),
                'id': card.get('id', ''),
                'artist': card.get('artist', 'Unknown'),
            }
            
            # 가격 정보 추출
            avg_price = None
            price_currency = None
            
            # CardMarket 가격 (유럽)
            if card_info['prices']:
                avg_price = card_info['prices'].get('averageSellPrice')
                price_currency = '€'
            
            # TCGPlayer 가격 (미국) - CardMarket이 없으면 사용
            if not avg_price and card_info['tcgplayer_prices']:
                # 다양한 가격 중 가장 일반적인 것 선택
                for price_type in ['normal', 'holofoil', 'reverseHolofoil', 'unlimitedHolofoil']:
                    if price_type in card_info['tcgplayer_prices']:
                        market_price = card_info['tcgplayer_prices'][price_type].get('market')
                        if market_price:
                            avg_price = market_price
                            price_currency = '$'
                            break
            
            card_info['avg_price'] = avg_price
            card_info['currency'] = price_currency
            
            cards.append(card_info)
        
        return cards, None
        
    except requests.exceptions.Timeout:
        return None, "API 응답이 느립니다. 잠시 후 다시 시도해주세요."
    except requests.exceptions.ConnectionError:
        return None, "인터넷 연결을 확인해주세요."
    except requests.exceptions.RequestException as e:
        return None, f"네트워크 오류: {str(e)}"
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def calculate_average_price(cards):
    """카드들의 평균 가격 계산"""
    prices = []
    for card in cards:
        if card.get('avg_price'):
            prices.append(float(card['avg_price']))
    
    if not prices:
        return None, None
    
    avg = sum(prices) / len(prices)
    currency = cards[0].get('currency', '$')
    
    return avg, currency

# 메인 컨텐츠
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "🔍 포켓몬 카드 검색",
        placeholder="예: Pikachu, Charizard, Mewtwo",
        help="영어로 포켓몬 이름을 입력하세요"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_button = st.button("검색", type="primary", use_container_width=True)

# 검색 실행
if search_button and search_query:
    with st.spinner("🔍 카드를 검색하는 중..."):
        cards, error = search_pokemon_cards(search_query)
        
        if error:
            st.error(f"⚠️ {error}")
            st.info("""
            ### 💡 검색 팁
            - 정확한 포켓몬 이름을 영어로 입력해보세요
            - 철자를 확인해보세요
            - 예: Pikachu, Charizard, Mewtwo
            """)
            
        elif not cards or len(cards) == 0:
            st.warning(f"'{search_query}'에 대한 검색 결과가 없습니다.")
            st.info("""
            ### 🔍 다른 검색어로 시도해보세요
            - 포켓몬의 영어 이름을 입력하세요
            - 예: Pikachu, Charizard, Bulbasaur
            """)
        
        else:
            st.success(f"✅ {len(cards)}개의 카드를 찾았습니다!")
            
            # 평균 가격 계산
            avg_price, currency = calculate_average_price(cards)
            
            if avg_price:
                st.markdown("### 💰 전체 평균 가격")
                col1, col2, col3 = st.columns(3)
                
                prices = [float(c['avg_price']) for c in cards if c.get('avg_price')]
                
                with col1:
                    st.metric("평균 가격", f"{currency}{avg_price:.2f}")
                with col2:
                    if prices:
                        st.metric("최저 가격", f"{currency}{min(prices):.2f}")
                with col3:
                    if prices:
                        st.metric("최고 가격", f"{currency}{max(prices):.2f}")
                
                st.markdown("---")
            
            # 카드 목록 표시
            st.markdown("### 🎴 검색 결과")
            
            # 3열 그리드로 표시
            for i in range(0, len(cards), 3):
                cols = st.columns(3)
                
                for j, col in enumerate(cols):
                    if i + j < len(cards):
                        card = cards[i + j]
                        
                        with col:
                            # 카드 이미지
                            if card.get('image'):
                                st.image(card['image'], use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/300x420?text=No+Image", use_container_width=True)
                            
                            # 카드 정보
                            st.markdown(f"**{card['name']}**")
                            st.caption(f"📦 {card['set']} • #{card['number']}")
                            
                            if card.get('rarity') != 'N/A':
                                st.caption(f"⭐ {card['rarity']}")
                            
                            # 가격
                            if card.get('avg_price'):
                                st.metric(
                                    "시장 평균 가격",
                                    f"{card['currency']}{card['avg_price']:.2f}"
                                )
                            else:
                                st.info("가격 정보 없음")
                            
                            # 상세 정보
                            with st.expander("상세 정보"):
                                st.write(f"**카드 ID**: {card['id']}")
                                st.write(f"**아티스트**: {card['artist']}")
                                
                                # 모든 가격 정보 표시
                                if card['prices']:
                                    st.write("**CardMarket 가격 (€)**")
                                    for key, value in card['prices'].items():
                                        if value:
                                            st.write(f"- {key}: €{value}")
                                
                                if card['tcgplayer_prices']:
                                    st.write("**TCGPlayer 가격 ($)**")
                                    for price_type, prices in card['tcgplayer_prices'].items():
                                        if isinstance(prices, dict):
                                            st.write(f"**{price_type}**:")
                                            for key, value in prices.items():
                                                if value:
                                                    st.write(f"  - {key}: ${value}")
                            
                            st.markdown("---")
            
            # 가격 차트
            if avg_price:
                st.markdown("### 📊 가격 분포")
                
                chart_data = []
                for card in cards:
                    if card.get('avg_price'):
                        chart_data.append({
                            '카드': f"{card['name'][:20]}...",
                            '가격': float(card['avg_price'])
                        })
                
                if chart_data:
                    df = pd.DataFrame(chart_data)
                    st.bar_chart(df.set_index('카드'))

elif search_button and not search_query:
    st.warning("검색어를 입력해주세요!")

