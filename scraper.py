import requests
import re
import pandas as pd

class SnkrdunkScraper:
    def __init__(self):
        self.base_url = "https://snkrdunk.com/en"
        self.api_url = "https://snkrdunk.com/en/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_cards(self, keyword):
        """키워드로 카드를 검색하고 결과 리스트를 반환합니다."""
        search_endpoint = f"{self.api_url}/search"
        params = {
            "keyword": keyword,
            "perPage": 21,
            "page": 1
        }
        
        try:
            response = requests.get(search_endpoint, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # Streetwear & TCG 섹션에서 카드 정보 추출
            cards = []
            for item in data.get('streetwears', []):
                # TCG 아이템인지 확인 (보통 카테고리나 이름으로 판단 가능)
                # API 응답 구조에 따라 적절히 필터링
                cards.append({
                    "id": item.get('id'),
                    "name": item.get('name'),
                    "thumbnail": item.get('thumbnailUrl'),
                    "min_price": item.get('minPrice'),
                    "url": f"{self.base_url}/trading-cards/{item.get('id')}"
                })
            return cards
        except Exception as e:
            print(f"Search error: {e}")
            return []

    def get_recent_prices(self, item_id):
        """특정 카드의 최근 거래 가격들을 가져옵니다."""
        # 'used' 페이지에서 SOLD 데이터를 추출 (API가 명확하지 않을 경우 HTML 파싱 병행)
        used_url = f"{self.base_url}/trading-cards/{item_id}/used"
        
        try:
            # HTML에서 직접 SOLD 가격 추출 시도
            response = requests.get(used_url, headers=self.headers)
            response.raise_for_status()
            html_content = response.text
            
            # 정규표현식을 사용하여 SOLD US $XX 패턴 추출
            # 예: SOLD US $71
            prices = []
            matches = re.findall(r"SOLD\s+US\s+\$([\d,]+)", html_content)
            
            for m in matches:
                price = int(m.replace(',', ''))
                prices.append(price)
            
            return prices
        except Exception as e:
            print(f"Price extraction error: {e}")
            return []

if __name__ == "__main__":
    # 간단한 테스트
    scraper = SnkrdunkScraper()
    print("Testing search for 'Pikachu'...")
    results = scraper.search_cards("Pikachu")
    if results:
        print(f"Found {len(results)} cards. First card: {results[0]['name']}")
        prices = scraper.get_recent_prices(results[0]['id'])
        print(f"Recent SOLD prices: {prices}")
