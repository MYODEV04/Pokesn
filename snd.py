import streamlit as st
import requests
from typing import Any, Dict, List, Optional
import json
import re


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
# 1) 강력한 필터링 함수
# -----------------------------
def is_pokemon_card(card: Dict[str, Any]) -> bool:
    """
    포켓몬 카드인지 **강력하게** 판별
    """
    if not isinstance(card, dict):
        return False
    
    # 전체 카드 정보를 문자열로 변환 (대소문자 무시)
    card_json = json.dumps(card, ensure_ascii=False).lower()
    card_name = card.get("name", "").lower()
    
    # === 1단계: 절대 제외 (다른 TCG) ===
    EXCLUDE_TCG = [
        # 원피스
        "one piece", "onepiece", "ワンピース", "ون بيس",
        "luffy", "zoro", "nami", "sanji", "chopper", "robin", "franky", "brook", "usopp",
        "monkey d", "roronoa", "nico robin", "don!! card", "don card",
        "romance dawn", "paramount war", "god's island", "adventure on god",
        "kumamoto special", "ultra deck", "starter deck",
        
        # 유희왕
        "yu-gi-oh", "yugioh", "遊戯王", "يوغي",
        "blue-eyes", "dark magician", "exodia",
        
        # MTG
        "magic the gathering", "mtg", "マジック",
        "planeswalker", "mana",
        
        # 디지몬
        "digimon", "デジモン",
        
        # 듀얼마스터즈
        "duel masters", "デュエル・マスターズ",
        
        # 바이스슈바르츠
        "weiss schwarz", "ヴァイスシュヴァルツ",
    ]
    
    for exclude in EXCLUDE_TCG:
        if exclude in card_json or exclude in card_name:
            return False
    
    # === 2단계: 박스/팩 제외 (싱글 카드만) ===
    BOX_KEYWORDS = [
        "booster box", "booster pack", "box set",
        "elite trainer box", "etb", "trainer box",
        "build & battle", "premium collection",
        "special collection", "ultra premium",
        "ブースターボックス", "ブースターパック",
        # 특수한 박스 상품들
        "collection box", "bundle", "case", "display"
    ]
    
    for box_kw in BOX_KEYWORDS:
        if box_kw in card_name or box_kw in card_json:
            # 단, "box"가 이름에 있어도 싱글 카드일 수 있으므로 더 확인
            # 예: "Pokémon Card from Box Set" 같은 경우
            pass
    
    # tradingCardCategory 확인
    category = card.get("tradingCardCategory", {})
    if isinstance(category, dict):
        cat_name = category.get("name", "").lower()
        cat_id = str(category.get("id", ""))
        
        # Box & Packs 카테고리면 제외
        if "box" in cat_name or "pack" in cat_name:
            return False
        
        # 카테고리 ID 14 = Box & Packs
        if cat_id == "14":
            return False
    
    # === 3단계: 포켓몬 확인 (반드시 포함되어야 함) ===
    POKEMON_KEYWORDS = [
        "pokemon", "pokémon", "ポケモン", "ポケカ",
        "pikachu", "charizard", "eevee", "mewtwo", "mew",
        "blastoise", "venusaur", "snorlax", "gengar",
        "gyarados", "dragonite", "umbreon", "espeon",
        "lucario", "greninja", "rayquaza", "latias",
        # 포켓몬 전용 용어
        "vmax", "vstar", "v-union", "gx", "ex card",
        "ultra rare", "secret rare", "full art",
        # 포켓몬 세트명
        "scarlet", "violet", "sword", "shield",
        "brilliant stars", "crown zenith", "silver tempest",
        "fusion strike", "evolving skies", "chilling reign",
        "battle styles", "vivid voltage", "champion's path",
        "detective pikachu", "team up", "unified minds"
    ]
    
    has_pokemon = False
    for pkm in POKEMON_KEYWORDS:
        if pkm in card_json or pkm in card_name:
            has_pokemon = True
            break
    
    # 브랜드 정보 확인
    brand = card.get("brand", {})
    if isinstance(brand, dict):
        brand_name = brand.get("name", "").lower()
        brand_id = str(brand.get("id", ""))
        
        if "pokemon" in brand_name or "pokémon" in brand_name:
            has_pokemon = True
        
        # 포켓몬 브랜드 ID (추정)
        if brand_id in ["1", "pokemon"]:
            has_pokemon = True
    
    # 세트명 확인
    set_name = card.get("setName", "").lower()
    if any(pkm in set_name for pkm in POKEMON_KEYWORDS):
        has_pokemon = True
    
    return has_pokemon


def is_single_card(card: Dict[str, Any]) -> bool:
    """
    싱글 카드인지 확인 (박스/팩 제외)
    """
    if not isinstance(card, dict):
        return False
    
    card_name = card.get("name", "").lower()
    
    # 명확한 박스/팩 키워드
    box_patterns = [
        r'\bbox\b', r'\bpack\b', r'\bbooster\b',
        r'\betb\b', r'\bcase\b', r'\bdisplay\b',
        r'\bbundle\b', r'\bcollection box\b'
    ]
    
    for pattern in box_patterns:
        if re.search(pattern, card_name, re.IGNORECASE):
            return False
    
    # 카테고리 확인
    category = card.get("tradingCardCategory", {})
    if isinstance(category, dict):
        cat_id = str(category.get("id", ""))
        if cat_id == "14":  # Box & Packs
            return False
    
    return True


# -----------------------------
# 2) SNKRDUNK API - 포켓몬 TCG 검색
# -----------------------------
def search_pokemon_tcg(
    character_name: str = "",
    set_name: str = "",
    card_number: str = "",
    page: int = 1,
    per_page: int = 30
) -> Dict[str, Any]:
    """
    포켓몬 TCG 싱글 카드 검색
    """
    
    # 검색 키워드 조합
    search_keywords = []
    
    # 항상 "Pokemon"을 기본으로 추가
    search_keywords.append("Pokemon")
    
    if character_name.strip():
        search_keywords.append(character_name.strip())
    if set_name.strip():
        search_keywords.append(set_name.strip())
    if card_number.strip():
        search_keywords.append(card_number.strip())
    
    keyword = " ".join(search_keywords)
    
    # API 엔드포인트 시도
    attempts = [
        # 시도 1: Pokemon + 싱글 카드 카테고리
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "keyword": keyword,
                "tradingCardCategoryId": "13",  # Single Cards
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
        # 시도 2: 기본 검색
        {
            "url": "https://snkrdunk.com/en/v1/trading-cards",
            "params": {
                "keyword": keyword,
                "page": page,
                "perPage": per_page,
                "sortType": "popular"
            }
        },
    ]
    
    all_pokemon_cards = []
    errors = []
    
    for idx, attempt in enumerate(attempts, 1):
        try:
            cleaned_params = {k: v for k, v in attempt["params"].items() if v}
            result = get_json(attempt["url"], cleaned_params)
            
            # 결과 추출
            items = extract_cards_from_response(result)
            
            if not items:
                errors.append({
                    "attempt": idx,
                    "status": "no_items"
                })
                continue
            
            # 강력한 필터링 적용
            for card in items:
                # 1차: 포켓몬 카드인지 확인
                if not is_pokemon_card(card):
                    continue
                
                # 2차: 싱글 카드인지 확인
                if not is_single_card(card):
                    continue
                
                all_pokemon_cards.append(card)
            
            # 포켓몬 카드를 찾았으면 성공
            if all_pokemon_cards:
                return {
                    "success": True,
                    "data": result,
                    "filtered_items": all_pokemon_cards,
                    "endpoint": attempt["url"],
                    "params": cleaned_params,
                    "attempt_number": idx,
                    "items_count": len(all_pokemon_cards),
                    "original_count": len(items),
                    "filtered_out": len(items) - len(all_pokemon_cards)
                }
            
        except Exception as e:
            errors.append({
                "attempt": idx,
                "error": str(e)
            })
    
    return {
        "success": False,
        "errors": errors,
        "total_attempts": len(attempts)
    }


# -----------------------------
# 3) 기존 함수들
# -----------------------------
def get_used_listings(card_id: str, per_page: int = 50, page: int = 1) -> Any:
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/used-listings"
    params = {
        "perPage": per_page,
        "page": page,
        "sortType": "latest",
        "isOnlyOnSale": "false",
    }
    return get_json(url, params=params)


def get_related_single_cards(card_id: str, per_page: int = 10, page: int = 1) -> Any:
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}/related-single-cards"
    params = {"perPage": per_page, "page": page}
    return get_json(url, params=params)


def get_card_detail(card_id: str) -> Any:
    url = f"https://snkrdunk.com/en/v1/trading-cards/{card_id}"
    return get_json(url)


def extract_cards_from_response(response_data: Any) -> List[Dict[str, Any]]:
    if not response_data:
        return []
    
    if isinstance(response_data, dict):
        for key in ["items", "list", "data", "results", "cards", "products", "tradingCards"]:
            if key in response_data and isinstance(response_data[key], list):
                return response_data[key]
        
        if "data" in response_data and isinstance(response_data["data"], dict):
            for key in ["items", "list", "results", "cards", "tradingCards"]:
                if key in response_data["data"] and isinstance(response_data["data"][key], list):
                    return response_data["data"][key]
    
    elif isinstance(response_data, list):
        return response_data
    
    return []


def extract_card_id(card_item: Dict[str, Any]) -> Optional[str]:
    if not isinstance(card_item, dict):
        return None
    
    id_fields = ["id", "cardId", "tradingCardId", "productId", "item_id", "_id", "itemId"]
    
    for field in id_fields:
        if field in card_item:
            return str(card_item[field])
    
    return None


def extract_listings_info(data: Any) -> Dict[str, Any]:
    listings_info = {
        "listings": [],
        "has_data": False,
        "total_count": 0
    }
    
    if not data:
        return listings_info
    
    listings = []
    
    if isinstance(data, dict):
        for key in ["items", "list", "data", "usedListings", "listings"]:
            if key in data and isinstance(data[key], list):
                listings = data[key]
                break
        
        if not listings and "data" in data:
            inner_data = data["data"]
            if isinstance(inner_data, list):
                listings = inner_data
            elif isinstance(inner_data, dict):
                for key in ["items", "list", "usedListings"]:
                    if key in inner_data and isinstance(inner_data[key], list):
                        listings = inner_data[key]
                        break
    
    elif isinstance(data, list):
        listings = data
    
    if not listings:
        return listings_info
    
    for listing in listings:
        if not isinstance(listing, dict):
            continue
        
        listing_data = {
            "price": None,
            "condition": None,
            "seller": None,
            "created_at": None,
            "is_on_sale": False
        }
        
        for price_key in ["price", "salePrice", "amount", "value", "sellPrice"]:
            if price_key in listing:
                try:
                    listing_data["price"] = float(listing[price_key])
                    break
                except (ValueError, TypeError):
                    pass
        
        for cond_key in ["condition", "grade", "quality", "tier"]:
            if cond_key in listing:
                listing_data["condition"] = str(listing[cond_key])
                break
        
        if "seller" in listing:
            seller = listing["seller"]
            if isinstance(seller, dict):
                listing_data["seller"] = seller.get("name") or seller.get("username")
            else:
                listing_data["seller"] = str(seller)
        
        for date_key in ["createdAt", "created_at", "listedAt", "date"]:
            if date_key in listing:
                listing_data["created_at"] = str(listing[date_key])
                break
        
        for sale_key in ["isOnSale", "is_on_sale", "available", "inStock"]:
            if sale_key in listing:
                listing_data["is_on_sale"] = bool(listing[sale_key])
                break
        
        if listing_data["price"] and listing_data["price"] > 0:
            listings_info["listings"].append(listing_data)
    
    listings_info["has_data"] = len(listings_info["listings"]) > 0
    listings_info["total_count"] = len(listings_info["listings"])
    
    return listings_info


def calculate_price_stats(listings: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not listings:
        return {
            "lowest_price": None,
            "highest_price": None,
            "average_price": None,
            "median_price": None,
            "total_listings": 0,
            "on_sale_count": 0
        }
    
    prices = [l["price"] for l in listings if l["price"] and l["price"] > 0]
    
    if not prices:
        return {
            "lowest_price": None,
            "highest_price": None,
            "average_price": None,
            "median_price": None,
            "total_listings": len(listings),
            "on_sale_count": sum(1 for l in listings if l.get("is_on_sale"))
        }
    
    prices.sort()
    
    return {
        "lowest_price": min(prices),
        "highest_price": max(prices),
        "average_price": sum(prices) / len(prices),
        "median_price": prices[len(prices) // 2],
        "total_listings": len(listings),
        "on_sale_count": sum(1 for l in listings if l.get("is_on_sale"))
    }


# -----------------------------
# 4) Streamlit UI
# -----------------------------
st.set_page_config(page_title="포켓몬 TCG 검색", layout="wide")

st.title("🎴 SNKRDUNK 포켓몬 TCG 검색기")
st.markdown("### 포켓몬 트레이딩 카드를 검색하세요")

st.success("✨ **강력한 필터링**: 원피스/유희왕 등 다른 카드 완전 차단!")

with st.sidebar:
    st.header("🔍 검색 옵션")
    
    search_mode = st.radio(
        "검색 방법",
        ["캐릭터/세트 검색", "Card ID 직접 입력"]
    )
    
    st.divider()
    
    if search_mode == "캐릭터/세트 검색":
        st.subheader("📝 검색 정보")
        
        character_name = st.text_input(
            "🎮 캐릭터명",
            value="Pikachu",
            placeholder="예: Pikachu, Charizard"
        )
        
        set_name = st.text_input(
            "📦 세트명 (선택)",
            value="",
            placeholder="예: Detective Pikachu, 151"
        )
        
        card_number = st.text_input(
            "🔢 카드 번호 (선택)",
            value="",
            placeholder="예: 025"
        )
        
        st.info(f"🔍 검색: Pokemon {character_name or ''} {set_name or ''} {card_number or ''}")
    
    else:
        st.subheader("🆔 Card ID")
        card_id = st.text_input("Card ID", value="", placeholder="예: 135232")
    
    st.divider()
    
    with st.expander("⚙️ 고급 옵션"):
        per_page = st.slider("검색 결과 수", 10, 50, 30)
        show_raw_json = st.checkbox("Raw JSON", value=False)
        show_debug = st.checkbox("디버그", value=False)
    
    search_button = st.button("🔍 검색 시작", type="primary", use_container_width=True)

if search_button:
    if search_mode == "캐릭터/세트 검색":
        with st.spinner("🔎 포켓몬 TCG 검색 중..."):
            search_result = search_pokemon_tcg(
                character_name=character_name,
                set_name=set_name,
                card_number=card_number,
                per_page=per_page
            )
            
            if not search_result.get("success"):
                st.error("❌ 검색 실패")
                
                if show_debug:
                    with st.expander("디버그"):
                        st.json(search_result.get("errors", []))
                st.stop()
            
            st.success(f"✅ {search_result.get('items_count', 0)}개 포켓몬 카드 발견!")
            
            if search_result.get('filtered_out', 0) > 0:
                st.warning(f"🚫 {search_result['filtered_out']}개 다른 카드 제외됨 (원피스 등)")
            
            cards = search_result.get("filtered_items", [])
            
            st.subheader("📋 검색 결과")
            
            for idx, card in enumerate(cards[:15], 1):
                with st.expander(f"🃏 #{idx} - {card.get('name', '이름 없음')}", expanded=(idx <= 3)):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        img_url = card.get("imageUrl") or card.get("image")
                        if img_url:
                            st.image(img_url, width=200)
                    
                    with col2:
                        st.markdown(f"**카드명:** {card.get('name', 'N/A')}")
                        st.markdown(f"**번호:** {card.get('number', 'N/A')}")
                        st.markdown(f"**세트:** {card.get('setName', 'N/A')}")
                        
                        if 'rarity' in card:
                            st.markdown(f"**레어도:** {card['rarity']}")
                        
                        extracted_id = extract_card_id(card)
                        if extracted_id:
                            st.markdown(f"**Card ID:** `{extracted_id}`")
                            
                            if st.button(f"💰 매물 보기", key=f"detail_{idx}"):
                                st.session_state['selected_card_id'] = extracted_id
                                st.rerun()
                    
                    if show_raw_json:
                        with st.expander("Raw JSON"):
                            st.json(card)
    
    else:
        if not card_id.strip():
            st.error("❌ Card ID를 입력해주세요")
            st.stop()
        st.session_state['selected_card_id'] = card_id.strip()

if 'selected_card_id' in st.session_state:
    selected_id = st.session_state['selected_card_id']
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("⬅️ 뒤로가기"):
            del st.session_state['selected_card_id']
            st.rerun()
    
    st.header(f"📊 카드 상세 정보")
    st.caption(f"Card ID: {selected_id}")
    
    try:
        tab1, tab2, tab3 = st.tabs(["💰 매물 정보", "🔗 관련 카드", "📝 상세"])
        
        with tab1:
            with st.spinner("매물 로딩..."):
                used_data = get_used_listings(selected_id)
                listings_info = extract_listings_info(used_data)
                
                if listings_info["has_data"]:
                    st.success(f"✅ {listings_info['total_count']}개 매물")
                    
                    stats = calculate_price_stats(listings_info["listings"])
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("💵 최저가", f"¥{stats['lowest_price']:,.0f}" if stats['lowest_price'] else "N/A")
                    col2.metric("💵 최고가", f"¥{stats['highest_price']:,.0f}" if stats['highest_price'] else "N/A")
                    col3.metric("💵 평균가", f"¥{stats['average_price']:,.0f}" if stats['average_price'] else "N/A")
                    col4.metric("📊 매물", f"{stats['total_listings']}개")
                    
                    if stats['total_listings'] > 1:
                        st.subheader("가격 분포")
                        prices = [l["price"] for l in listings_info["listings"] if l["price"]]
                        st.bar_chart(prices)
                    
                    st.divider()
                    st.subheader("매물 목록")
                    
                    for idx, listing in enumerate(listings_info["listings"][:20], 1):
                        with st.expander(
                            f"#{idx} - ¥{listing['price']:,.0f}" +
                            (f" ({listing['condition']})" if listing['condition'] else "") +
                            (" 🟢" if listing.get('is_on_sale') else "")
                        ):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**가격:** ¥{listing['price']:,.0f}")
                                if listing['condition']:
                                    st.markdown(f"**컨디션:** {listing['condition']}")
                            with col2:
                                if listing['seller']:
                                    st.markdown(f"**판매자:** {listing['seller']}")
                                if listing['created_at']:
                                    st.markdown(f"**등록:** {listing['created_at'][:10]}")
                else:
                    st.info("💡 매물 없음")
                
                if show_raw_json:
                    with st.expander("Raw JSON"):
                        st.json(used_data)
        
        with tab2:
            with st.spinner("관련 카드..."):
                related_data = get_related_single_cards(selected_id)
                related_cards = extract_cards_from_response(related_data)
                
                # 관련 카드도 필터링
                filtered_related = [c for c in related_cards if is_pokemon_card(c) and is_single_card(c)]
                
                if filtered_related:
                    st.subheader(f"🔗 관련 카드 ({len(filtered_related)}개)")
                    
                    cols = st.columns(3)
                    for idx, card in enumerate(filtered_related[:9]):
                        with cols[idx % 3]:
                            st.markdown(f"**{card.get('name', 'N/A')}**")
                            
                            img_url = card.get("imageUrl") or card.get("image")
                            if img_url:
                                st.image(img_url, width=150)
                            
                            related_id = extract_card_id(card)
                            if related_id:
                                if st.button("보기", key=f"rel_{idx}"):
                                    st.session_state['selected_card_id'] = related_id
                                    st.rerun()
                else:
                    st.info("💡 관련 카드 없음")
        
        with tab3:
            try:
                detail_data = get_card_detail(selected_id)
                
                if isinstance(detail_data, dict):
                    st.subheader("기본 정보")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**이름:** {detail_data.get('name', 'N/A')}")
                        st.markdown(f"**번호:** {detail_data.get('number', 'N/A')}")
                    with col2:
                        st.markdown(f"**세트:** {detail_data.get('setName', 'N/A')}")
                        st.markdown(f"**레어도:** {detail_data.get('rarity', 'N/A')}")
                
                st.divider()
                st.json(detail_data)
                
            except Exception as e:
                st.warning(f"⚠️ {str(e)}")
    
    except Exception as e:
        st.error(f"❌ 오류: {str(e)}")

st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>🎴 포켓몬 TCG 전용 검색기</p>
    <p>🚫 원피스/유희왕 등 다른 카드 자동 차단</p>
</div>
""", unsafe_allow_html=True)
