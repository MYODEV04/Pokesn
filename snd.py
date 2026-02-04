import streamlit as st
import requests
from typing import Any, Dict, List, Optional
import json


# -----------------------------
# 0) 공통 HTTP 유틸
# -----------------------------
def get_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    SNKRDUNK에 GET 요청을 보내고 JSON으로 응답을 파싱해서 반환한다.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://snkrdunk.com/",
    }

    r = requests.get(url, headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# -----------------------------
# 1) SNKRDUNK API - 포켓몬 카드 전용 검색
# -----------------------------
def search_pokemon_cards(
    character_name: str = "",
    set_name: str = "",
    card_number: str = "",
    page: int = 1,
    per_page: int = 20
) -> Dict[str, Any]:
    """
    포켓몬 카드만 검색 (brandId=pokemon 사용)
    캐릭터명, 세트명, 카드번호로 검색
    """
    
    # 검색 키워드 조합
    search_keywords = []
    if character_name.strip():
        search_keywords.append(character_name.strip())
    if set_name.strip():
        search_keywords.append(set_name.strip())
    if card_number.strip():
        search_keywords.append(card_number.strip())
    
    keyword = " ".join(search_keywords) if search_keywords else ""
    
    if not keyword:
        return {
            "success": False,
            "error": "검색어를 입력해주세요",
            "data": None
        }
    
    # 포켓몬 전용 API 엔드포인트 시도
    attempts = [
        # 시도 1: brands/pokemon 경로 사용
        {
            "url": "https://snkrdunk.com/en/v1/brands/pokemon/trading-cards",
            "params": {
                "keyword": keyword,
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
        # 시도 2: brandId 파라미터 사용
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "brandId": "pokemon",
                "keyword": keyword,
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
        # 시도 3: brand 파라미터
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "brand": "pokemon",
                "keyword": keyword,
                "page": page,
                "perPage": per_page
            }
        },
        # 시도 4: categoryId 25 (포켓몬 카테고리로 추정)
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "categoryId": "25",
                "keyword": keyword,
                "page": page,
                "perPage": per_page
            }
        },
        # 시도 5: q 파라미터 + brandId
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "brandId": "pokemon",
                "q": keyword,
                "page": page,
                "perPage": per_page
            }
        },
        # 시도 6: 검색어에 Pokemon 추가
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "keyword": f"Pokemon {keyword}",
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
        # 시도 7: name 파라미터 + brandId
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "brandId": "pokemon",
                "name": keyword,
                "page": page,
                "perPage": per_page
            }
        },
    ]
    
    errors = []
    
    for idx, attempt in enumerate(attempts, 1):
        try:
            # 빈 파라미터 제거
            cleaned_params = {k: v for k, v in attempt["params"].items() if v}
            
            result = get_json(attempt["url"], cleaned_params)
            
            # 결과가 있는지 확인
            items = extract_cards_from_response(result)
            
            # 포켓몬 카드만 필터링
            pokemon_items = filter_pokemon_only(items)
            
            if pokemon_items:  # 포켓몬 카드가 있으면 성공
                return {
                    "success": True,
                    "data": result,
                    "filtered_items": pokemon_items,
                    "endpoint": attempt["url"],
                    "params": cleaned_params,
                    "attempt_number": idx,
                    "items_count": len(pokemon_items),
                    "original_count": len(items)
                }
            else:
                # 결과는 받았지만 포켓몬 카드가 없음
                errors.append({
                    "attempt": idx,
                    "url": attempt["url"],
                    "params": cleaned_params,
                    "status": "no_pokemon_items",
                    "total_items": len(items),
                    "response_keys": list(result.keys()) if isinstance(result, dict) else None
                })
                
        except Exception as e:
            errors.append({
                "attempt": idx,
                "url": attempt["url"],
                "params": attempt["params"],
                "error": str(e)
            })
    
    # 모든 시도 실패
    return {
        "success": False,
        "errors": errors,
        "total_attempts": len(attempts)
    }


def filter_pokemon_only(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    포켓몬 카드만 필터링 (원피스, 유희왕 등 제외)
    """
    if not cards:
        return []
    
    # 원피스 관련 키워드 (제외할 것들)
    exclude_keywords = [
        "one piece", "onepiece", "ワンピース", 
        "luffy", "zoro", "nami", "sanji", "chopper",
        "monkey d", "roronoa", "god's island",
        "romance dawn", "paramount war", "nico robin",
        "yu-gi-oh", "yugioh", "遊戯王",
        "magic the gathering", "mtg",
        "digimon", "デジモン"
    ]
    
    # 포켓몬 관련 키워드 (확실한 것만 포함)
    pokemon_keywords = [
        "pokemon", "pokémon", "ポケモン", "ポケカ",
        "pikachu", "charizard", "eevee", "mewtwo",
        "scarlet", "violet", "sword", "shield",
        "vmax", "vstar", "ex", "gx", "trainer"
    ]
    
    filtered = []
    
    for card in cards:
        # 카드 전체 텍스트를 JSON으로 변환하여 검색
        card_text = json.dumps(card, ensure_ascii=False).lower()
        
        # 제외 키워드가 있으면 스킵
        has_exclude = any(keyword in card_text for keyword in exclude_keywords)
        if has_exclude:
            continue
        
        # 포켓몬 키워드가 있으면 포함
        has_pokemon = any(keyword in card_text for keyword in pokemon_keywords)
        
        # 브랜드나 카테고리 정보 확인
        brand_info = card.get("brand", {})
        if isinstance(brand_info, dict):
            brand_name = brand_info.get("name", "").lower()
            if "pokemon" in brand_name or "pokémon" in brand_name:
                has_pokemon = True
        
        # 세트명 확인
        set_name = card.get("setName", "").lower()
        if "pokemon" in set_name or "pokémon" in set_name:
            has_pokemon = True
        
        if has_pokemon:
            filtered.append(card)
    
    return filtered


# -----------------------------
# 2) SNKRDUNK API - 기존 확정된 엔드포인트
# -----------------------------
def get_used_listings(card_id: str, per_page: int = 16, page: int = 1) -> Any:
    """
    카드ID 기준으로 used-listings(중고 리스팅/가격 관련) JSON을 가져온다.
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/used-listings"
    params = {
        "perPage": per_page,
        "page": page,
        "sortType": "latest",
        "isOnlyOnSale": "false",
    }
    return get_json(url, params=params)


def get_related_single_cards(card_id: str, per_page: int = 10, page: int = 1) -> Any:
    """
    카드ID 기준으로 related-single-cards(유사 상품) JSON을 가져온다.
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/related-single-cards"
    params = {
        "perPage": per_page,
        "page": page,
    }
    return get_json(url, params=params)


def get_card_detail(card_id: str) -> Any:
    """
    카드 상세 정보 가져오기
    """
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}"
    return get_json(url)


# -----------------------------
# 3) 검색 결과에서 카드 정보 추출
# -----------------------------
def extract_cards_from_response(response_data: Any) -> List[Dict[str, Any]]:
    """
    검색 응답에서 카드 정보 추출 (다양한 구조 지원)
    """
    if not response_data:
        return []
    
    cards = []
    
    # 다양한 응답 구조 처리
    if isinstance(response_data, dict):
        # 패턴 1: 최상위 레벨에 리스트
        for key in ["items", "list", "data", "results", "cards", "products", "tradingCards"]:
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        
        # 패턴 2: 중첩된 구조 (data.items 등)
        if "data" in response_data and isinstance(response_data["data"], dict):
            for key in ["items", "list", "results", "cards", "tradingCards"]:
                if key in response_data["data"] and isinstance(response_data["data"][key], list):
                    return response_data["data"][key]
        
        # 패턴 3: response.data.items
        if "response" in response_data and isinstance(response_data["response"], dict):
            if "data" in response_data["response"]:
                inner_data = response_data["response"]["data"]
                if isinstance(inner_data, list):
                    return inner_data
                elif isinstance(inner_data, dict):
                    for key in ["items", "list", "cards"]:
                        if key in inner_data and isinstance(inner_data[key], list):
                            return inner_data[key]
    
    # 패턴 4: 최상위가 리스트인 경우
    elif isinstance(response_data, list):
        return response_data
    
    return cards


def extract_card_id(card_item: Dict[str, Any]) -> Optional[str]:
    """
    카드 아이템에서 ID 추출
    """
    if not isinstance(card_item, dict):
        return None
    
    # 가능한 ID 필드명들
    id_fields = ["id", "cardId", "tradingCardId", "productId", "item_id", "_id", "itemId"]
    
    for field in id_fields:
        if field in card_item:
            return str(card_item[field])
    
    return None


# -----------------------------
# 4) 가격 정보 추출
# -----------------------------
def extract_price_info(data: Any) -> Dict[str, Any]:
    """
    JSON에서 가격 정보 추출
    """
    price_info = {
        "lowest_price": None,
        "highest_price": None,
        "average_price": None,
        "all_prices": []
    }
    
    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = key.lower()
                if any(price_key in key_lower for price_key in ["price", "amount", "value"]):
                    if isinstance(value, (int, float)) and value > 0:
                        price_info["all_prices"].append(float(value))
                    elif isinstance(value, str):
                        try:
                            price_val = float(value.replace(",", "").replace("¥", "").replace("$", ""))
                            if price_val > 0:
                                price_info["all_prices"].append(price_val)
                        except:
                            pass
            
            for value in obj.values():
                walk(value)
        
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    
    walk(data)
    
    if price_info["all_prices"]:
        price_info["lowest_price"] = min(price_info["all_prices"])
        price_info["highest_price"] = max(price_info["all_prices"])
        price_info["average_price"] = sum(price_info["all_prices"]) / len(price_info["all_prices"])
    
    return price_info


# -----------------------------
# 5) Streamlit UI
# -----------------------------
st.set_page_config(page_title="SNKRDUNK 포켓몬 카드 검색", layout="wide")

st.title("🃏 SNKRDUNK 포켓몬 카드 검색기")
st.markdown("### 캐릭터명과 카드팩으로 포켓몬 카드를 검색하세요")

# 경고 메시지
st.info("✨ **업데이트**: 이제 포켓몬 카드만 정확하게 필터링됩니다! (원피스 카드 제외)")

# 사이드바
with st.sidebar:
    st.header("🔍 검색 옵션")
    
    search_mode = st.radio(
        "검색 방법",
        ["캐릭터/카드팩 검색", "Card ID 직접 입력"],
        help="캐릭터명과 카드팩으로 검색하거나, 알고 있는 Card ID를 직접 입력"
    )
    
    st.divider()
    
    if search_mode == "캐릭터/카드팩 검색":
        st.subheader("📝 검색 정보 입력")
        
        character_name = st.text_input(
            "🎮 캐릭터명",
            value="Pikachu",
            placeholder="예: Pikachu, Charizard, Eevee",
            help="포켓몬 이름을 입력하세요"
        )
        
        set_name = st.text_input(
            "📦 카드팩 이름 (선택)",
            value="",
            placeholder="예: Scarlet Violet, 151",
            help="특정 카드팩에서만 검색하려면 입력하세요"
        )
        
        card_number = st.text_input(
            "🔢 카드 번호 (선택)",
            value="",
            placeholder="예: 025, 098",
            help="특정 번호의 카드만 찾으려면 입력하세요"
        )
        
        # 검색 조건 요약
        st.info(f"🔍 검색 조건\n캐릭터: {character_name or '미지정'}\n카드팩: {set_name or '전체'}\n번호: {card_number or '전체'}")
        
        # 검색 예시
        with st.expander("💡 검색 예시"):
            st.markdown("""
            **기본 검색:**
            - 캐릭터명: `Pikachu`
            - 카드팩: (비움)
            - 번호: (비움)
            
            **세트 내 검색:**
            - 캐릭터명: `Pikachu`
            - 카드팩: `Scarlet Violet`
            - 번호: (비움)
            
            **정확한 카드:**
            - 캐릭터명: `Charizard`
            - 카드팩: `151`
            - 번호: `006`
            
            **인기 캐릭터:**
            - Pikachu (피카츄)
            - Charizard (리자몽)
            - Eevee (이브이)
            - Mewtwo (뮤츠)
            - Umbreon (블래키)
            - Gengar (팬텀)
            
            **인기 카드팩:**
            - Scarlet Violet
            - 151
            - Crown Zenith
            - Silver Tempest
            - Fusion Strike
            """)
    
    else:  # Card ID 직접 입력
        st.subheader("🆔 Card ID 입력")
        card_id = st.text_input(
            "Card ID",
            value="135232",
            placeholder="예: 135232",
            help="SNKRDUNK 카드 페이지 URL에서 확인 가능"
        )
        
        st.caption("💡 **Card ID 찾는 법:**")
        st.caption("1. SNKRDUNK에서 카드 클릭")
        st.caption("2. URL 확인: `.../135232` ← 이 숫자")
    
    st.divider()
    
    # 고급 옵션
    with st.expander("⚙️ 고급 옵션"):
        per_page = st.slider("검색 결과 수", 5, 50, 20)
        show_raw_json = st.checkbox("Raw JSON 표시", value=False)
        show_debug = st.checkbox("디버그 정보", value=False)
    
    search_button = st.button("🔍 검색 시작", type="primary", use_container_width=True)

# 메인 컨텐츠
if search_button:
    if search_mode == "캐릭터/카드팩 검색":
        # 최소 하나는 입력했는지 확인
        if not character_name.strip() and not set_name.strip() and not card_number.strip():
            st.error("❌ 캐릭터명, 카드팩 이름, 또는 카드 번호 중 최소 하나는 입력해주세요!")
            st.stop()
        
        with st.spinner(f"🔎 포켓몬 카드 검색 중... 여러 방법을 시도하고 있어요!"):
            # 검색 API 호출
            search_result = search_pokemon_cards(
                character_name=character_name,
                set_name=set_name,
                card_number=card_number,
                per_page=per_page
            )
            
            if not search_result.get("success"):
                st.error("❌ 검색 실패 - 포켓몬 카드를 찾을 수 없습니다")
                
                st.markdown("""
                **다음을 시도해보세요:**
                1. 캐릭터명만 간단히 입력 (예: "Pikachu")
                2. 영문 이름 사용
                3. 철자 확인
                4. Card ID 직접 입력 모드 사용
                """)
                
                if show_debug and "errors" in search_result:
                    with st.expander("🔧 디버그 정보"):
                        st.json(search_result["errors"])
                        st.caption(f"총 {search_result.get('total_attempts', 0)}번 시도했습니다")
                st.stop()
            
            # 검색 성공!
            st.success(f"✅ 검색 성공! ({search_result.get('items_count', 0)}개 포켓몬 카드 발견)")
            
            if search_result.get('original_count', 0) > search_result.get('items_count', 0):
                filtered_out = search_result['original_count'] - search_result['items_count']
                st.caption(f"🚫 {filtered_out}개의 다른 카드(원피스 등)는 자동으로 제외되었습니다")
            
            if show_debug:
                st.caption(f"엔드포인트: {search_result.get('endpoint')}")
                st.caption(f"시도 #{search_result.get('attempt_number')} 성공")
                with st.expander("사용된 파라미터"):
                    st.json(search_result.get('params'))
            
            # 필터링된 포켓몬 카드 목록
            cards = search_result.get("filtered_items", [])
            
            if not cards:
                st.warning("⚠️ 포켓몬 카드를 찾을 수 없습니다")
                st.stop()
            
            st.info(f"📊 총 {len(cards)}개의 포켓몬 카드를 찾았습니다")
            
            # 카드 목록 표시
            st.subheader("📋 검색 결과 (포켓몬 카드만)")
            
            for idx, card in enumerate(cards[:15], 1):  # 최대 15개 표시
                with st.expander(f"🃏 #{idx} - {card.get('name', card.get('title', '이름 없음'))}", expanded=(idx <= 3)):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # 이미지 표시
                        img_url = None
                        for img_key in ["imageUrl", "image", "thumbnailUrl", "thumbnail", "img", "picture"]:
                            if img_key in card:
                                img_url = card[img_key]
                                break
                        
                        if img_url:
                            st.image(img_url, width=200)
                        else:
                            st.info("🖼️ 이미지 없음")
                    
                    with col2:
                        # 카드 정보
                        st.markdown(f"**카드명:** {card.get('name', card.get('title', 'N/A'))}")
                        st.markdown(f"**번호:** {card.get('number', card.get('cardNumber', 'N/A'))}")
                        st.markdown(f"**세트:** {card.get('setName', card.get('series', card.get('set', 'N/A')))}")
                        
                        # 추가 정보
                        if 'rarity' in card:
                            st.markdown(f"**레어도:** {card['rarity']}")
                        if 'type' in card:
                            st.markdown(f"**타입:** {card['type']}")
                        
                        # Card ID 추출
                        extracted_id = extract_card_id(card)
                        if extracted_id:
                            st.markdown(f"**Card ID:** `{extracted_id}`")
                            
                            if st.button(f"💰 가격 정보 보기", key=f"detail_{idx}"):
                                st.session_state['selected_card_id'] = extracted_id
                                st.rerun()
                        else:
                            st.caption("⚠️ Card ID를 찾을 수 없습니다")
                    
                    if show_raw_json:
                        with st.expander("📄 Raw JSON"):
                            st.json(card)
            
            if len(cards) > 15:
                st.info(f"💡 {len(cards) - 15}개의 추가 결과가 더 있습니다")
            
            # 전체 응답 JSON
            if show_raw_json:
                with st.expander("📄 전체 응답 JSON"):
                    st.json(search_result["data"])
    
    else:  # Card ID 직접 입력
        if not card_id.strip():
            st.error("❌ Card ID를 입력해주세요")
            st.stop()
        st.session_state['selected_card_id'] = card_id.strip()

# 선택된 카드 상세 정보 표시
if 'selected_card_id' in st.session_state:
    selected_id = st.session_state['selected_card_id']
    
    st.divider()
    
    # 뒤로가기 버튼
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("⬅️ 뒤로가기"):
            del st.session_state['selected_card_id']
            st.rerun()
    
    st.header(f"📊 카드 상세 정보")
    st.caption(f"Card ID: {selected_id}")
    
    try:
        tab1, tab2, tab3 = st.tabs(["💰 가격 정보", "🔗 관련 카드", "📝 카드 상세"])
        
        with tab1:
            with st.spinner("가격 정보 로딩 중..."):
                used_data = get_used_listings(selected_id)
                price_info = extract_price_info(used_data)
                
                if price_info["all_prices"]:
                    # 가격 통계
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("💵 최저가", f"¥{price_info['lowest_price']:,.0f}")
                    col2.metric("💵 최고가", f"¥{price_info['highest_price']:,.0f}")
                    col3.metric("💵 평균가", f"¥{price_info['average_price']:,.0f}")
                    col4.metric("📊 리스팅", f"{len(price_info['all_prices'])}개")
                    
                    # 가격 분포 차트
                    if len(price_info["all_prices"]) > 1:
                        st.subheader("가격 분포")
                        st.bar_chart(price_info["all_prices"])
                    
                    # 가격 분석
                    st.subheader("💡 가격 분석")
                    price_range = price_info['highest_price'] - price_info['lowest_price']
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("가격 차이", f"¥{price_range:,.0f}")
                    with col2:
                        variance = (price_range / price_info['average_price'] * 100) if price_info['average_price'] > 0 else 0
                        st.metric("가격 변동성", f"{variance:.1f}%")
                else:
                    st.info("💡 현재 판매 중인 리스팅이 없습니다")
                
                if show_raw_json:
                    with st.expander("📄 Raw JSON - Used Listings"):
                        st.json(used_data)
        
        with tab2:
            with st.spinner("관련 카드 로딩 중..."):
                related_data = get_related_single_cards(selected_id)
                related_cards = extract_cards_from_response(related_data)
                
                # 관련 카드도 포켓몬만 필터링
                related_cards = filter_pokemon_only(related_cards)
                
                if related_cards:
                    st.subheader(f"🔗 관련 포켓몬 카드 ({len(related_cards)}개)")
                    
                    # 그리드 형식
                    cols = st.columns(3)
                    for idx, card in enumerate(related_cards[:9]):
                        with cols[idx % 3]:
                            st.markdown(f"**{card.get('name', 'N/A')}**")
                            
                            img_url = card.get("imageUrl") or card.get("image")
                            if img_url:
                                st.image(img_url, width=150)
                            
                            related_id = extract_card_id(card)
                            if related_id:
                                if st.button("보기", key=f"related_{idx}"):
                                    st.session_state['selected_card_id'] = related_id
                                    st.rerun()
                else:
                    st.info("💡 관련 포켓몬 카드가 없습니다")
                
                if show_raw_json:
                    with st.expander("📄 Raw JSON - Related Cards"):
                        st.json(related_data)
        
        with tab3:
            with st.spinner("카드 상세 정보 로딩 중..."):
                try:
                    detail_data = get_card_detail(selected_id)
                    
                    if isinstance(detail_data, dict):
                        st.subheader("📝 기본 정보")
                        
                        info_cols = st.columns(2)
                        with info_cols[0]:
                            st.markdown(f"**이름:** {detail_data.get('name', 'N/A')}")
                            st.markdown(f"**번호:** {detail_data.get('number', 'N/A')}")
                            st.markdown(f"**세트:** {detail_data.get('setName', 'N/A')}")
                        with info_cols[1]:
                            st.markdown(f"**레어도:** {detail_data.get('rarity', 'N/A')}")
                            st.markdown(f"**타입:** {detail_data.get('type', 'N/A')}")
                    
                    st.divider()
                    st.subheader("📄 전체 데이터")
                    st.json(detail_data)
                    
                except Exception as e:
                    st.warning(f"⚠️ 상세 정보를 가져올 수 없습니다: {str(e)}")
    
    except requests.HTTPError as e:
        st.error(f"❌ HTTP 에러: {e}")
        st.info("💡 Card ID를 확인해주세요")
    except Exception as e:
        st.error(f"❌ 오류: {str(e)}")
        if show_debug:
            st.exception(e)

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>💡 <b>Tip:</b> 캐릭터명만 입력해도 검색됩니다!</p>
    <p>🔧 여러 API 조합을 자동으로 시도하여 최적의 결과를 찾습니다</p>
    <p>✨ 포켓몬 카드만 정확하게 필터링됩니다 (원피스 카드 자동 제외)</p>
</div>
""", unsafe_allow_html=True)
