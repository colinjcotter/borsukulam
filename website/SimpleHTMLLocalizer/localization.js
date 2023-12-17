var dictionary = {
    "_": {
        "last_updated": "Last updated",
        "temperature": "Temperature",
        "pressure": "Pressure",
        "longitude": "Longitude",
        "latitude": "Latitude"
    },
    "ar": {
        "last_updated": "آخر تحديث",
        "temperature": "درجة الحرارة",
        "pressure": "الضغط الجوي",
        "longitude": "خط الطول",
        "latitude": "خط العرض"
    },
    "zh": {
        "last_updated": "最后更新",
        "temperature": "温度",
        "pressure": "气压",
        "longitude": "经度",
        "latitude": "纬度"
    },
    "zh-TW": {
        "last_updated": "最後更新",
        "temperature": "溫度",
        "pressure": "氣壓",
        "longitude": "經度",
        "latitude": "緯度"
    },
    "en": {
        "last_updated": "Last Updated",
        "temperature": "Temperature",
        "pressure": "Pressure",
        "longitude": "Longitude",
        "latitude": "Latitude"
    },
    "fr": {
        "last_updated": "Dernière mise à jour",
        "temperature": "Température",
        "pressure": "Pression",
        "longitude": "Longitude",
        "latitude": "Latitude"
    },
    "de": {
        "last_updated": "Zuletzt aktualisiert",
        "temperature": "Temperatur",
        "pressure": "Luftdruck",
        "longitude": "Längengrad",
        "latitude": "Breitengrad"
    },
    "it": {
        "last_updated": "Ultimo Aggiornamento",
        "temperature": "Temperatura",
        "pressure": "Pressione",
        "longitude": "Longitudine",
        "latitude": "Latitudine"
    },
    "ja": {
        "last_updated": "最終更新",
        "temperature": "温度",
        "pressure": "気圧",
        "longitude": "経度",
        "latitude": "緯度"
    },
    "ko": {
        "last_updated": "최종 업데이트",
        "temperature": "온도",
        "pressure": "기압",
        "longitude": "경도",
        "latitude": "위도"
    },
    "pt": {
        "last_updated": "Última Atualização",
        "temperature": "Temperatura",
        "pressure": "Pressão",
        "longitude": "Longitude",
        "latitude": "Latitude"
    },
    "ru": {
        "last_updated": "Последнее обновление",
        "temperature": "Температура",
        "pressure": "Давление",
        "longitude": "Долгота",
        "latitude": "Широта"
    },
    "es": {
        "last_updated": "Última Actualización",
        "temperature": "Temperatura",
        "pressure": "Presión",
        "longitude": "Longitud",
        "latitude": "Latitud"
    },
    "vi": {
        "last_updated": "Cập nhật cuối cùng",
        "temperature": "Nhiệt độ",
        "pressure": "Áp suất không khí",
        "longitude": "Kinh độ",
        "latitude": "Vĩ độ"
    }
};



class HTMLLocalizer {
    constructor() {
        customElements.define('localized-text', LocalizedTextElement);
    }
}

class LocalizedTextElement extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        var key = this.hasAttribute('key') ? this.getAttribute('key') : ''; 
        var lang = this.hasAttribute('lang') ? this.getAttribute('lang') : this.getLang();
        this.innerHTML = this.translate(key, lang);
    }

    getLang() {
        var lang = (navigator.languages != undefined)?navigator.languages[0]:navigator.language;
        // Ignore country code (example: en-US -> en)
        return lang.split("-")[0];
    }
    
    translate(key, lang) {
        return (lang in dictionary)?dictionary[lang][key]:dictionary['_'][key];
    }
}
  
new HTMLLocalizer();
