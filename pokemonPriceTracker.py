import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time

import sys
import subprocess
subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])

# 페이지 설정
st.set_page_config(
    page_title="SNKRDUNK 포켓몬 카드 가격 검색",
    page_icon="🎴",
    layout="wide"
)

# 제목
st.title("🎴 SNKRDUNK 포켓몬 카드 가격 검색")
st.markdown("SNKRDUNK에서 포켓몬 카드의 최근 거래가격을 확인해보세요!")

# 사이드바
st.sidebar.header("📖 사용 방법")
st.sidebar.markdown("""
1. 포켓몬 이름을 영어로 입력하세요
2. 카드 번호를 입력하세요 (선택)
3. 검색 버튼을 클릭하세요

### 🔍 검색 예시
- **이름**: Pikachu
- **번호**: 025
- **이름 + 번호**: Charizard 006

### 💡 팁
- 영어 이름으로 검색하세요
- 카드 번호는 선택사항입니다
""")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📊 데이터 출처
[SNKRDUNK.com](https://snkrdunk.com)

실시간 시장 데이터를 제공합니다.
""")

# 헤더 설정 (403 에러 회피)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0',
}

def search_snkrdunk_pokemon(pokemon_name, card_number=None):
    """SNKRDUNK에서 포켓몬 카드 검색"""
    try:
        # 검색어 생성
        search_query = pokemon_name
        if card_number:
            search_query = f"{pokemon_name} {card_number}"
        
        # SNKRDUNK 검색 URL (예상)
        search_url = f"https://snkrdunk.com/en/search?q={search_query.replace(' ', '+')}"
        
        st.info(f"검색 URL: {search_url}")
        
        # 세션 사용
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # 요청
        response = session.get(search_url, timeout=10)
        
        if response.status_code == 403:
            return None, "접근이 차단되었습니다. SNKRDUNK는 자동화된 접근을 제한하고 있습니다."
        
        if response.status_code != 200:
            return None, f"HTTP 에러: {response.status_code}"
        
        # HTML 파싱
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 검색 결과 추출 (실제 HTML 구조에 따라 조정 필요)
        cards = []
        
        # 여기에 실제 SNKRDUNK HTML 구조에 맞는 파싱 코드 추가
        # 예시 구조 (실제와 다를 수 있음)
        card_items = soup.find_all('div', class_='product-item')
        
        for item in card_items:
            try:
                # 카드 정보 추출
                card_data = {
                    'name': None,
                    'price': None,
                    'image': None,
                    'url': None,
                    'condition': None
                }
                
                # 제목 추출
                title_elem = item.find('h3') or item.find('a', class_='product-title')
                if title_elem:
                    card_data['name'] = title_elem.get_text(strip=True)
                
                # 가격 추출
                price_elem = item.find('span', class_='price') or item.find('div', class_='price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # 숫자만 추출
                    price_match = re.search(r'[\d,]+', price_text)
                    if price_match:
                        card_data['price'] = price_match.group().replace(',', '')
                
                # 이미지 URL 추출
                img_elem = item.find('img')
                if img_elem:
                    card_data['image'] = img_elem.get('src') or img_elem.get('data-src')
                
                # 상품 URL 추출
                link_elem = item.find('a')
                if link_elem:
                    card_data['url'] = link_elem.get('href')
                    if card_data['url'] and not card_data['url'].startswith('http'):
                        card_data['url'] = f"https://snkrdunk.com{card_data['url']}"
                
                cards.append(card_data)
            except Exception as e:
                continue
        
        return cards, None
        
    except requests.exceptions.Timeout:
        return None, "요청 시간 초과"
    except requests.exceptions.ConnectionError:
        return None, "연결 오류"
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def calculate_average_price(prices):
    """최근 거래가격의 평균 계산"""
    if not prices:
        return None
    
    valid_prices = [float(p) for p in prices if p and p.replace(',', '').replace('.', '').isdigit()]
    
    if not valid_prices:
        return None
    
    return sum(valid_prices) / len(valid_prices)

# 메인 컨텐츠
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    pokemon_name = st.text_input(
        "🔍 포켓몬 이름 (영어)",
        placeholder="예: Pikachu, Charizard, Mewtwo",
        help="영어로 포켓몬 이름을 입력하세요"
    )

with col2:
    card_number = st.text_input(
        "🔢 카드 번호 (선택)",
        placeholder="예: 025",
        help="카드 번호를 입력하세요 (선택사항)"
    )

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    search_button = st.button("검색", type="primary", use_container_width=True)

# 중요 공지
st.warning("""
⚠️ **중요 공지:**

SNKRDUNK는 자동화된 웹 스크래핑을 방지하기 위해 보안 조치를 사용합니다. 
이 앱은 교육 목적의 예시이며, 실제로는 다음 방법들을 권장합니다:

1. **공식 API 사용** (가능한 경우)
2. **Selenium + 크롬 드라이버** 사용 (브라우저 자동화)
3. **수동 검색** 후 데이터 입력
4. **SNKRDUNK 앱** 직접 사용

아래는 대안 솔루션입니다 👇
""")

# 검색 실행
if search_button and pokemon_name:
    with st.spinner("카드를 검색하는 중..."):
        cards, error = search_snkrdunk_pokemon(pokemon_name, card_number)
        
        if error:
            st.error(f"⚠️ {error}")
            
            # 대안 제시
            st.info("""
            ### 🔄 대안 방법
            
            **1. SNKRDUNK 직접 방문:**
            - [SNKRDUNK Pokemon Cards](https://snkrdunk.com/en/brands/pokemon/trading-cards)
            
            **2. Selenium 사용:**
            - 브라우저 자동화 도구 사용
            - 더 안정적인 스크래핑 가능
            
            **3. 수동 데이터 입력:**
            - SNKRDUNK에서 가격을 확인한 후
            - 이 앱에서 수동으로 입력하여 평균 계산
            """)
            
        elif not cards or len(cards) == 0:
            st.warning("검색 결과가 없습니다.")
            st.info(f"[SNKRDUNK에서 직접 검색하기](https://snkrdunk.com/en/search?q={pokemon_name.replace(' ', '+')})")
        
        else:
            st.success(f"✅ {len(cards)}개의 카드를 찾았습니다!")
            
            # 카드 목록 표시
            st.markdown("### 검색 결과")
            
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
                            if card.get('name'):
                                st.markdown(f"**{card['name']}**")
                            
                            # 가격
                            if card.get('price'):
                                st.metric("가격", f"¥{card['price']}")
                            
                            # 링크
                            if card.get('url'):
                                st.link_button("SNKRDUNK에서 보기", card['url'], use_container_width=True)
                            
                            st.markdown("---")

elif search_button and not pokemon_name:
    st.warning("포켓몬 이름을 입력해주세요!")

# 수동 입력 섹션
st.markdown("---")
st.markdown("## 📊 수동 가격 평균 계산기")
st.markdown("SNKRDUNK에서 직접 확인한 가격들을 입력하여 평균을 계산하세요.")

with st.expander("💰 가격 데이터 입력", expanded=False):
    st.markdown("쉼표(,)로 구분하여 여러 가격을 입력하세요. 예: 1000, 1200, 950, 1100")
    
    manual_prices = st.text_area(
        "최근 거래 가격들 (엔화)",
        placeholder="예: 1000, 1200, 950, 1100, 1050",
        help="쉼표로 구분하여 입력하세요"
    )
    
    if st.button("평균 계산", type="secondary"):
        if manual_prices:
            try:
                # 가격 파싱
                prices_list = [p.strip() for p in manual_prices.split(',')]
                valid_prices = []
                
                for price in prices_list:
                    # 숫자만 추출
                    clean_price = re.sub(r'[^\d.]', '', price)
                    if clean_price:
                        valid_prices.append(float(clean_price))
                
                if valid_prices:
                    avg_price = sum(valid_prices) / len(valid_prices)
                    min_price = min(valid_prices)
                    max_price = max(valid_prices)
                    
                    st.success("✅ 계산 완료!")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("평균 가격", f"¥{avg_price:,.0f}")
                    with col2:
                        st.metric("최저 가격", f"¥{min_price:,.0f}")
                    with col3:
                        st.metric("최고 가격", f"¥{max_price:,.0f}")
                    
                    # 차트 표시
                    if len(valid_prices) > 1:
                        st.markdown("### 📈 가격 분포")
                        df = pd.DataFrame({
                            '거래 순서': range(1, len(valid_prices) + 1),
                            '가격': valid_prices
                        })
                        st.line_chart(df.set_index('거래 순서'))
                else:
                    st.error("유효한 가격을 찾을 수 없습니다.")
            except Exception as e:
                st.error(f"오류: {str(e)}")
        else:
            st.warning("가격을 입력해주세요!")

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>데이터 출처: <a href='https://snkrdunk.com/en' target='_blank'>SNKRDUNK.com</a></p>
    <p>⚠️ 이 도구는 교육 목적입니다. 실제 거래는 SNKRDUNK 사이트에서 진행하세요.</p>
</div>
""", unsafe_allow_html=True)
