import streamlit as st
import pandas as pd
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
1. 검색어를 영어로 입력하세요
2. 검색 버튼을 클릭하세요

### 🔍 검색 예시
- **포켓몬 이름**: Pikachu
- **특정 카드**: Detective Pikachu SV-P 098
- **세트 번호**: Charizard 006
- **일반 검색**: Mewtwo

### 💡 팁
- 영어 이름으로 검색하세요
- 카드 번호를 함께 입력하면 더 정확해요
- 첫 검색은 시간이 걸릴 수 있습니다
""")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 📊 데이터 출처
[SNKRDUNK.com](https://snkrdunk.com)

실시간 시장 데이터를 제공합니다.
""")

@st.cache_resource
def get_driver():
    """Selenium WebDriver 초기화 (캐싱)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    return driver

def search_snkrdunk_pokemon_selenium(pokemon_name):
    """Selenium을 사용하여 SNKRDUNK에서 포켓몬 카드 검색"""
    try:
        driver = get_driver()
        
        # 검색어 사용
        search_query = pokemon_name
        
        # SNKRDUNK 검색 URL
        search_url = f"https://snkrdunk.com/en/search?q={search_query.replace(' ', '+')}"
        
        # 페이지 로드
        driver.get(search_url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 검색 결과 대기
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='product'], div[class*='item'], article"))
            )
        except TimeoutException:
            return None, "검색 결과를 찾을 수 없습니다."
        
        # 페이지 소스 가져오기
        page_source = driver.page_source
        
        # BeautifulSoup으로 파싱 (html.parser 사용 - 더 안정적)
        soup = BeautifulSoup(page_source, 'html.parser')
        
        cards = []
        
        # 다양한 선택자 시도 (SNKRDUNK의 실제 구조에 맞게)
        possible_selectors = [
            {'tag': 'div', 'class': 'product-item'},
            {'tag': 'div', 'class': 'ProductCard'},
            {'tag': 'article', 'class': None},
            {'tag': 'div', 'attrs': {'data-testid': 'product-card'}},
            {'tag': 'a', 'class': None},  # 링크 기반 검색
        ]
        
        card_elements = []
        for selector in possible_selectors:
            elements = []
            try:
                if selector.get('class'):
                    # class 속성으로 검색
                    elements = soup.find_all(selector['tag'], class_=selector['class'])
                    # 정규식으로도 시도
                    if not elements:
                        elements = soup.find_all(selector['tag'], attrs={'class': re.compile(selector['class'], re.I)})
                elif selector.get('attrs'):
                    elements = soup.find_all(selector['tag'], attrs=selector['attrs'])
                else:
                    elements = soup.find_all(selector['tag'])
                
                if elements:
                    card_elements = elements[:20]  # 최대 20개
                    break
            except Exception as e:
                continue
        
        # 카드 정보 추출
        for item in card_elements:
            try:
                card_data = {
                    'name': None,
                    'price': None,
                    'image': None,
                    'url': None,
                }
                
                # 제목/이름 추출
                title_selectors = ['h3', 'h2', 'p', 'span']
                for tag in title_selectors:
                    title_elem = item.find(tag)
                    if title_elem and len(title_elem.get_text(strip=True)) > 3:
                        card_data['name'] = title_elem.get_text(strip=True)
                        break
                
                # 가격 추출
                price_patterns = [r'¥\s*[\d,]+', r'\$\s*[\d,]+', r'[\d,]+\s*円']
                text_content = item.get_text()
                for pattern in price_patterns:
                    price_match = re.search(pattern, text_content)
                    if price_match:
                        price_text = price_match.group()
                        # 숫자만 추출
                        numbers = re.sub(r'[^\d]', '', price_text)
                        if numbers:
                            card_data['price'] = numbers
                            break
                
                # 이미지 URL 추출
                img_elem = item.find('img')
                if img_elem:
                    card_data['image'] = img_elem.get('src') or img_elem.get('data-src')
                    # 상대 경로를 절대 경로로 변환
                    if card_data['image'] and not card_data['image'].startswith('http'):
                        card_data['image'] = f"https://snkrdunk.com{card_data['image']}"
                
                # 상품 URL 추출
                link_elem = item.find('a')
                if link_elem:
                    card_data['url'] = link_elem.get('href')
                    if card_data['url'] and not card_data['url'].startswith('http'):
                        card_data['url'] = f"https://snkrdunk.com{card_data['url']}"
                elif item.name == 'a':
                    card_data['url'] = item.get('href')
                    if card_data['url'] and not card_data['url'].startswith('http'):
                        card_data['url'] = f"https://snkrdunk.com{card_data['url']}"
                
                # 유효한 데이터가 있는 경우만 추가
                if card_data['name'] or card_data['price']:
                    cards.append(card_data)
                    
            except Exception as e:
                continue
        
        return cards, None
        
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

def calculate_average_price(prices):
    """최근 거래가격의 평균 계산"""
    if not prices:
        return None
    
    valid_prices = []
    for p in prices:
        if p and str(p).replace(',', '').replace('.', '').isdigit():
            valid_prices.append(float(str(p).replace(',', '')))
    
    if not valid_prices:
        return None
    
    return sum(valid_prices) / len(valid_prices)

# 메인 컨텐츠
col1, col2 = st.columns([3, 1])

with col1:
    pokemon_name = st.text_input(
        "🔍 검색어 (포켓몬 이름 또는 카드 번호 포함)",
        placeholder="예: Pikachu, Detective Pikachu SV-P 098, Charizard 006",
        help="영어로 포켓몬 이름을 입력하세요. 카드 번호도 함께 입력 가능합니다."
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    search_button = st.button("검색", type="primary", use_container_width=True)

# 안내 메시지
st.info("""
💡 **참고사항:**
- 첫 검색은 브라우저를 초기화하므로 10-15초 정도 걸릴 수 있습니다
- 이후 검색은 더 빨라집니다
- Selenium을 사용하여 실제 브라우저처럼 데이터를 가져옵니다
""")

# 검색 실행
if search_button and pokemon_name:
    with st.spinner("🔍 카드를 검색하는 중... (최대 15초 소요)"):
        cards, error = search_snkrdunk_pokemon_selenium(pokemon_name)
        
        if error:
            st.error(f"⚠️ {error}")
            
            # 대안 제시
            st.info(f"""
            ### 🔄 다른 방법
            
            **직접 확인하기:**
            - [SNKRDUNK에서 직접 검색하기](https://snkrdunk.com/en/search?q={pokemon_name.replace(' ', '+')})
            
            **문제 해결:**
            - 다른 포켓몬 이름으로 시도해보세요
            - 영어 철자를 확인해보세요
            - 잠시 후 다시 시도해보세요
            """)
            
        elif not cards or len(cards) == 0:
            st.warning("검색 결과가 없습니다.")
            st.info(f"[SNKRDUNK에서 직접 검색하기](https://snkrdunk.com/en/search?q={pokemon_name.replace(' ', '+')})")
        
        else:
            st.success(f"✅ {len(cards)}개의 카드를 찾았습니다!")
            
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
                                try:
                                    st.image(card['image'], use_container_width=True)
                                except:
                                    st.image("https://via.placeholder.com/300x420?text=No+Image", use_container_width=True)
                            else:
                                st.image("https://via.placeholder.com/300x420?text=No+Image", use_container_width=True)
                            
                            # 카드 정보
                            if card.get('name'):
                                st.markdown(f"**{card['name'][:50]}**")
                            
                            # 가격
                            if card.get('price'):
                                st.metric("가격", f"¥{int(card['price']):,}")
                            
                            # 링크
                            if card.get('url'):
                                st.link_button("SNKRDUNK에서 보기", card['url'], use_container_width=True)
                            
                            st.markdown("---")
            
            # 가격 통계
            prices = [card.get('price') for card in cards if card.get('price')]
            if prices:
                st.markdown("### 📊 가격 통계")
                
                avg_price = calculate_average_price(prices)
                valid_prices = [float(p) for p in prices if str(p).replace(',', '').isdigit()]
                
                if valid_prices:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("평균 가격", f"¥{int(avg_price):,}")
                    with col2:
                        st.metric("최저 가격", f"¥{int(min(valid_prices)):,}")
                    with col3:
                        st.metric("최고 가격", f"¥{int(max(valid_prices)):,}")

elif search_button and not pokemon_name:
    st.warning("검색어를 입력해주세요!")

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
    <p>🤖 Selenium 기반 자동 검색 | ⚠️ 실제 거래는 SNKRDUNK 사이트에서 진행하세요.</p>
</div>
""", unsafe_allow_html=True)
