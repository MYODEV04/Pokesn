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
st.markdown("포켓몬 카드의 실시간 시장 가격을 확인해보세요!")

# 사이드바에 API 키 입력
st.sidebar.header("⚙️ 설정")
api_key = st.sidebar.text_input(
    "API Key", 
    type="password",
    help="pokemonpricetracker.com에서 발급받은 API 키를 입력하세요"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📖 사용 방법
1. API Key를 입력하세요
2. 포켓몬 이름 또는 카드 번호를 검색하세요
3. 결과에서 원하는 카드를 선택하세요

### 🔗 API Key 발급
[PokemonPriceTracker.com](https://www.pokemonpricetracker.com/sign-up)
""")

# API 베이스 URL
BASE_URL = "https://www.pokemonpricetracker.com/api/v2"

def search_cards(query, api_key, set_id=None):
    """포켓몬 카드 검색"""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    params = {
        "search": query,
        "limit": 50
    }
    
    if set_id:
        params["setId"] = set_id
    
    try:
        response = requests.get(f"{BASE_URL}/cards", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 오류: {str(e)}")
        return None

def get_card_with_history(tcg_player_id, api_key, days=30):
    """카드 상세 정보 및 가격 히스토리 조회"""
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    params = {
        "tcgPlayerId": tcg_player_id,
        "includeHistory": "true",
        "days": days
    }
    
    try:
        response = requests.get(f"{BASE_URL}/cards", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 오류: {str(e)}")
        return None

# 메인 컨텐츠
if not api_key:
    st.warning("⚠️ 왼쪽 사이드바에서 API Key를 입력해주세요!")
    st.info("💡 무료 API Key는 하루 100회 요청이 가능합니다.")
else:
    # 검색 영역
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "🔍 포켓몬 이름 또는 카드 번호 검색",
            placeholder="예: Charizard, Pikachu, 025 등",
            help="포켓몬 이름(영문) 또는 카드 번호를 입력하세요"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        search_button = st.button("검색", type="primary", use_container_width=True)
    
    # 검색 실행
    if search_button and search_query:
        with st.spinner("카드를 검색하는 중..."):
            results = search_cards(search_query, api_key)
            
            if results and results.get("data"):
                cards = results["data"]
                st.success(f"✅ {len(cards)}개의 카드를 찾았습니다!")
                
                # 카드 목록을 그리드로 표시
                st.markdown("### 검색 결과")
                
                # 카드를 3개씩 나열
                for i in range(0, len(cards), 3):
                    cols = st.columns(3)
                    
                    for j, col in enumerate(cols):
                        if i + j < len(cards):
                            card = cards[i + j]
                            
                            with col:
                                # 카드 이미지
                                if card.get("image") and card["image"].get("large"):
                                    st.image(card["image"]["large"], use_container_width=True)
                                
                                # 카드 정보
                                st.markdown(f"**{card.get('name', 'N/A')}**")
                                st.caption(f"{card.get('setName', 'N/A')} - {card.get('cardNumber', 'N/A')}/{card.get('totalSetNumber', 'N/A')}")
                                st.caption(f"희귀도: {card.get('rarity', 'N/A')}")
                                
                                # 가격 정보
                                prices = card.get("prices", {})
                                if prices:
                                    st.markdown("#### 💰 가격")
                                    
                                    market_price = prices.get("market")
                                    if market_price:
                                        st.metric("시장가", f"${market_price:.2f}")
                                    
                                    col_a, col_b = st.columns(2)
                                    with col_a:
                                        low_price = prices.get("low")
                                        if low_price:
                                            st.metric("최저가", f"${low_price:.2f}")
                                    
                                    with col_b:
                                        high_price = prices.get("high")
                                        if high_price:
                                            st.metric("최고가", f"${high_price:.2f}")
                                
                                # 상세 정보 버튼
                                if st.button("상세 보기", key=f"detail_{card.get('tcgPlayerId')}", use_container_width=True):
                                    st.session_state.selected_card = card.get("tcgPlayerId")
                                
                                st.markdown("---")
                
                # 선택된 카드의 상세 정보 표시
                if hasattr(st.session_state, 'selected_card'):
                    st.markdown("## 📊 카드 상세 정보")
                    
                    with st.spinner("상세 정보를 불러오는 중..."):
                        detail_data = get_card_with_history(st.session_state.selected_card, api_key, days=30)
                        
                        if detail_data and detail_data.get("data"):
                            card_detail = detail_data["data"][0]
                            
                            col_left, col_right = st.columns([1, 2])
                            
                            with col_left:
                                if card_detail.get("image") and card_detail["image"].get("large"):
                                    st.image(card_detail["image"]["large"])
                            
                            with col_right:
                                st.markdown(f"### {card_detail.get('name', 'N/A')}")
                                st.markdown(f"**세트:** {card_detail.get('setName', 'N/A')}")
                                st.markdown(f"**카드 번호:** {card_detail.get('cardNumber', 'N/A')}/{card_detail.get('totalSetNumber', 'N/A')}")
                                st.markdown(f"**희귀도:** {card_detail.get('rarity', 'N/A')}")
                                st.markdown(f"**TCGPlayer ID:** {card_detail.get('tcgPlayerId', 'N/A')}")
                                
                                # 현재 가격 정보
                                prices = card_detail.get("prices", {})
                                if prices:
                                    st.markdown("#### 💵 현재 시장 가격")
                                    price_cols = st.columns(4)
                                    
                                    with price_cols[0]:
                                        if prices.get("market"):
                                            st.metric("시장가", f"${prices['market']:.2f}")
                                    with price_cols[1]:
                                        if prices.get("low"):
                                            st.metric("최저가", f"${prices['low']:.2f}")
                                    with price_cols[2]:
                                        if prices.get("mid"):
                                            st.metric("중간가", f"${prices['mid']:.2f}")
                                    with price_cols[3]:
                                        if prices.get("high"):
                                            st.metric("최고가", f"${prices['high']:.2f}")
                            
                            # 가격 히스토리 차트
                            if card_detail.get("priceHistory"):
                                st.markdown("#### 📈 가격 추이 (최근 30일)")
                                
                                history = card_detail["priceHistory"]
                                df = pd.DataFrame(history)
                                
                                if not df.empty and "date" in df.columns:
                                    df["date"] = pd.to_datetime(df["date"])
                                    df = df.sort_values("date")
                                    
                                    # 차트 생성
                                    chart_data = df.set_index("date")
                                    
                                    # 사용 가능한 가격 컬럼만 선택
                                    price_columns = [col for col in ["market", "low", "mid", "high"] if col in chart_data.columns]
                                    
                                    if price_columns:
                                        st.line_chart(chart_data[price_columns])
                                        
                                        # 통계 정보
                                        st.markdown("#### 📊 통계")
                                        stat_cols = st.columns(len(price_columns))
                                        
                                        for idx, col_name in enumerate(price_columns):
                                            with stat_cols[idx]:
                                                avg_price = df[col_name].mean()
                                                st.metric(
                                                    f"{col_name.capitalize()} 평균",
                                                    f"${avg_price:.2f}"
                                                )
                                else:
                                    st.info("가격 히스토리 데이터가 없습니다.")
                            else:
                                st.info("💡 가격 히스토리는 유료 플랜에서 이용 가능합니다.")
            else:
                st.warning("검색 결과가 없습니다. 다른 검색어를 시도해보세요.")
    
    elif search_button and not search_query:
        st.warning("검색어를 입력해주세요!")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>데이터 제공: <a href='https://www.pokemonpricetracker.com' target='_blank'>PokemonPriceTracker.com</a></p>
    <p>가격은 24시간마다 업데이트됩니다.</p>
</div>
""", unsafe_allow_html=True)
