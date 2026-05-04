import streamlit as st
from lunar_python import Lunar, Solar
import math
import datetime
import pytz
from datetime import timedelta


# --- 1. 門派基礎類與具體實現 ---

class SectBase:
    def __init__(self, name):
        self.name = name

    def get_si_hua_rules(self):
        raise NotImplementedError

    def get_interpretation(self, source_type, hua_type, target_palace_name, star_name=None):
        raise NotImplementedError

    def get_special_flags(self):
        return {}


class QinTianSect(SectBase):
    def __init__(self):
        super().__init__("欽天門")

    def get_si_hua_rules(self):
        return {
            "甲": ["廉貞", "破軍", "武曲", "太陽"],
            "乙": ["天機", "天梁", "紫微", "太陰"],
            "丙": ["天同", "天機", "文昌", "廉貞"],
            "丁": ["太陰", "天同", "天機", "巨門"],
            "戊": ["貪狼", "太陰", "右弼", "天機"],
            "己": ["武曲", "貪狼", "天梁", "文曲"],
            "庚": ["太陽", "武曲", "太陰", "天同"],
            "辛": ["巨門", "太陽", "文曲", "文昌"],
            "壬": ["天梁", "紫微", "左輔", "武曲"],
            "癸": ["破軍", "巨門", "太陰", "貪狼"],
        }

    def get_interpretation(self, source_type, hua_type, target_palace_name, star_name=None):
        base_msg = f"{source_type}化{hua_type}入{target_palace_name}"
        if hua_type == "忌":
            return f"{base_msg}：此為欠債之象,需注意該領域的執著與壓力。"
        elif hua_type == "祿":
            return f"{base_msg}：此為緣起之象,代表機會、喜歡與流動。"
        elif hua_type == "權":
            return f"{base_msg}：此為掌控之象,代表競爭、權力與變動。"
        elif hua_type == "科":
            return f"{base_msg}:此為名聲之象,代表平穩、貴人與緩和。"
        return f"{base_msg}:吉凶參半,需視星曜組合而定。"


class SanHeSect(SectBase):
    def __init__(self):
        super().__init__("三合派")

    def get_si_hua_rules(self):
        return {
            "甲": ["廉貞", "破軍", "武曲", "太陽"],
            "乙": ["天機", "天梁", "紫微", "太陰"],
            "丙": ["天同", "天機", "文昌", "廉貞"],
            "丁": ["太陰", "天同", "天機", "巨門"],
            "戊": ["貪狼", "太陰", "天機", "右弼"],
            "己": ["武曲", "貪狼", "天梁", "文曲"],
            "庚": ["太陽", "武曲", "太陰", "天同"],
            "辛": ["巨門", "太陽", "文曲", "文昌"],
            "壬": ["天梁", "紫微", "天府", "武曲"],
            "癸": ["破軍", "巨門", "太陰", "貪狼"],
        }

    def get_interpretation(self, source_type, hua_type, target_palace_name, star_name=None):
        msg = f"{source_type}化{hua_type}入{target_palace_name}"
        if star_name:
            msg += f" ({star_name})"
        if hua_type == "祿":
            return f"{msg}:主進財、人緣好,若星曜廟旺則吉力倍增。"
        elif hua_type == "忌":
            return f"{msg}:主波折、損失,若星曜落陷則凶性加重。"
        elif hua_type == "權":
            return f"{msg}:主爭奪、權力,事業上有突破但也伴隨壓力。"
        elif hua_type == "科":
            return f"{msg}:主名聲、學識,遇事可逢凶化吉。"
        return msg


# 時區 → 標準經線(用於真太陽時校正)
TZ_STANDARD_LONGITUDE = {
    "Asia/Taipei": 120.0,
    "Asia/Shanghai": 120.0,
    "Asia/Hong_Kong": 120.0,
    "Asia/Tokyo": 135.0,
    "America/New_York": -75.0,
    "America/Los_Angeles": -120.0,
    "America/Chicago": -90.0,
    "Europe/London": 0.0,
    "Europe/Paris": 15.0,
    "Europe/Berlin": 15.0,
    "Australia/Sydney": 150.0,
    "Pacific/Auckland": 180.0,
}


# --- 2. 核心排盤引擎 ---

class QintianZiweiGold:
    def __init__(self, year, month, day, hour, minute, gender,
                 longitude=121.5, sect_name="欽天門", timezone_str="Asia/Taipei"):
        self.gender = gender
        self.longitude = longitude
        self.timezone_str = timezone_str

        # 1. 真太陽時校正(只校正 經度時差 + 均時差,不雙重套用時區)
        self.solar_time, self.dst_active = self._get_true_solar_time(
            year, month, day, hour, minute, timezone_str
        )

        # 2. 創建 Solar 對象(使用校正後的時間)
        self.solar = Solar.fromYmdHms(
            self.solar_time.year, self.solar_time.month, self.solar_time.day,
            self.solar_time.hour, self.solar_time.minute, 0
        )
        self.lunar = self.solar.getLunar()

        # 基礎資訊
        self.year_gan = self.lunar.getYearGan()
        self.year_zhi = self.lunar.getYearZhi()
        self.month_zhi = self.lunar.getMonthZhi()
        self.hour_zhi = self.lunar.getTimeZhi()
        self.day_num = self.lunar.getDay()

        self.zhi_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
        self.gan_list = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

        # 初始化十二宮
        self.palaces = {}
        for zhi in self.zhi_list:
            self.palaces[zhi] = {
                "zhi": zhi, "gan": "", "name": "",
                "stars": [], "si_hua_out": [], "si_hua_in": []
            }

        # 選擇門派
        if sect_name == "三合派":
            self.sect = SanHeSect()
        else:
            self.sect = QinTianSect()

        # 排盤流程
        self._set_palace_gan()
        self.ming_zhi = self._get_ming_gong()
        self.shen_zhi = self._get_shen_gong()
        self._set_palace_names()
        self.wuxing_ju = self._calculate_wuxing_ju()
        self._arrange_14_major_stars()
        self._arrange_auxiliary_stars()
        self._arrange_misc_stars()
        self._arrange_birth_si_hua()
        self._calculate_flying_stars()

        self.analysis_report = self._generate_analysis()

    def _get_true_solar_time(self, year, month, day, hour, minute, timezone_str):
        """
        真太陽時校正:
        1. 經度時差 = (出生地經度 − 時區標準經線) × 4 分鐘
        2. 均時差 EOT(分鐘)
        3. 若該時刻處於 DST,當地時鐘比標準時快 1 小時 → 倒扣 60 分鐘
        不轉 UTC 再加經度時差(會雙重位移)。
        """
        local_dt = datetime.datetime(year, month, day, hour, minute, 0)
        dst_active = False

        try:
            tz = pytz.timezone(timezone_str)
            localized = tz.localize(local_dt, is_dst=None)
            dst_active = localized.dst() != timedelta(0)
        except Exception as e:
            st.warning(f"時區解析異常 {e},以無 DST 處理")

        std_longitude = TZ_STANDARD_LONGITUDE.get(timezone_str, 120.0)
        long_diff_min = (self.longitude - std_longitude) * 4.0

        day_of_year = datetime.date(year, month, day).timetuple().tm_yday
        B = 2 * math.pi * (day_of_year - 81) / 365.0
        eot_min = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

        total_offset = long_diff_min + eot_min
        if dst_active:
            total_offset -= 60.0

        return local_dt + timedelta(minutes=total_offset), dst_active

    def _get_index(self, item, lst):
        return lst.index(item)

    def _set_palace_gan(self):
        start_gan_map = {
            "甲": "丙", "己": "丙", "乙": "戊", "庚": "戊",
            "丙": "庚", "辛": "庚", "丁": "壬", "壬": "壬",
            "戊": "甲", "癸": "甲"
        }
        start_gan = start_gan_map[self.year_gan]
        start_idx = self.gan_list.index(start_gan)
        for i in range(12):
            zhi_idx = (2 + i) % 12  # 從寅宮起
            gan_idx = (start_idx + i) % 10
            self.palaces[self.zhi_list[zhi_idx]]["gan"] = self.gan_list[gan_idx]

    def _get_ming_gong(self):
        month_val = self.lunar.getMonth()
        hour_val = self._get_index(self.hour_zhi, self.zhi_list)
        idx = (2 + month_val - 1 - hour_val) % 12
        return self.zhi_list[idx]

    def _get_shen_gong(self):
        month_val = self.lunar.getMonth()
        hour_val = self._get_index(self.hour_zhi, self.zhi_list)
        idx = (2 + month_val - 1 + hour_val) % 12
        return self.zhi_list[idx]

    def _set_palace_names(self):
        names = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄",
                 "遷移", "交友", "官祿", "田宅", "福德", "父母"]
        ming_idx = self._get_index(self.ming_zhi, self.zhi_list)
        for i, name in enumerate(names):
            target_idx = (ming_idx - i) % 12
            self.palaces[self.zhi_list[target_idx]]["name"] = name
        self.palaces[self.shen_zhi]["name"] += "(身)"

    def _calculate_wuxing_ju(self):
        ming_gan = self.palaces[self.ming_zhi]["gan"]
        key = f"{ming_gan}{self.ming_zhi}"
        na_yin_full = {
            "甲子": 2, "乙丑": 2, "丙寅": 6, "丁卯": 6, "戊辰": 5, "己巳": 5,
            "庚午": 5, "辛未": 5, "壬申": 4, "癸酉": 4, "甲戌": 6, "乙亥": 6,
            "丙子": 2, "丁丑": 2, "戊寅": 5, "己卯": 5, "庚辰": 4, "辛巳": 4,
            "壬午": 5, "癸未": 5, "甲申": 2, "乙酉": 2, "丙戌": 5, "丁亥": 5,
            "戊子": 6, "己丑": 6, "庚寅": 5, "辛卯": 5, "壬辰": 2, "癸巳": 2,
            "甲午": 6, "乙未": 6, "丙申": 6, "丁酉": 6, "戊戌": 5, "己亥": 5,
            "庚子": 5, "辛丑": 5, "壬寅": 4, "癸卯": 4, "甲辰": 6, "乙巳": 6,
            "丙午": 2, "丁未": 2, "戊申": 5, "己酉": 5, "庚戌": 4, "辛亥": 4,
            "壬子": 5, "癸丑": 5, "甲寅": 2, "乙卯": 2, "丙辰": 5, "丁巳": 5,
            "戊午": 6, "己未": 6, "庚申": 4, "辛酉": 4, "壬戌": 2, "癸亥": 2,
        }
        ju_num = na_yin_full.get(key, 3)
        self.ju_num = ju_num
        return {2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局"}[ju_num]

    def _arrange_14_major_stars(self):
        """
        紫微定盤 — 採 iztro 開源庫驗證過的演算法 (cross-checked with 紫微斗數全書「安星訣」):
          1. offset=0; 找最小 offset 使 (day+offset) % ju == 0
          2. quotient = (day+offset)//ju, quotient %= 12
          3. ziwei_idx (iztro 索引, 0=寅) = quotient-1
          4. offset 偶 → +offset; 奇 → -offset
          5. 轉成本程式索引 (0=子): our = (iztro+2) % 12
        天府逆排於紫微對宮: tianfu_iztro = (12 - ziwei_iztro) % 12
        14 主星 offsets 依「天府順行有太陰,貪狼而後巨門臨,隨來天相天梁繼,七殺空三是破軍」
        → 破軍 offset = +10 (不是 +7)
        """
        day = self.day_num
        ju = self.ju_num

        offset = 0
        while (day + offset) % ju != 0:
            offset += 1
        quotient = ((day + offset) // ju) % 12
        ziwei_iztro = quotient - 1
        if offset % 2 == 0:
            ziwei_iztro += offset
        else:
            ziwei_iztro -= offset
        ziwei_iztro %= 12
        # 轉換: iztro 0=寅 → 本程式 0=子
        ziwei_idx = (ziwei_iztro + 2) % 12

        self.palaces[self.zhi_list[ziwei_idx]]["stars"].append("紫微")
        offsets_ziwei = {"天機": -1, "太陽": -3, "武曲": -4, "天同": -5, "廉貞": -8}
        for star, off in offsets_ziwei.items():
            idx = (ziwei_idx + off) % 12
            self.palaces[self.zhi_list[idx]]["stars"].append(star)

        # 天府 = 紫微對宮 (寅申軸對稱)。iztro: tianfu_iztro = (12 - ziwei_iztro) % 12
        tianfu_iztro = (12 - ziwei_iztro) % 12
        tianfu_idx = (tianfu_iztro + 2) % 12
        self.palaces[self.zhi_list[tianfu_idx]]["stars"].append("天府")
        offsets_tianfu = {"太陰": 1, "貪狼": 2, "巨門": 3,
                          "天相": 4, "天梁": 5, "七殺": 6, "破軍": 10}
        for star, off in offsets_tianfu.items():
            idx = (tianfu_idx + off) % 12
            self.palaces[self.zhi_list[idx]]["stars"].append(star)

    def _arrange_auxiliary_stars(self):
        month = self.lunar.getMonth()
        hour_idx = self._get_index(self.hour_zhi, self.zhi_list)
        self.palaces[self.zhi_list[(4 + month - 1) % 12]]["stars"].append("左輔")
        self.palaces[self.zhi_list[(10 - (month - 1)) % 12]]["stars"].append("右弼")
        self.palaces[self.zhi_list[(10 - hour_idx) % 12]]["stars"].append("文昌")
        self.palaces[self.zhi_list[(4 + hour_idx) % 12]]["stars"].append("文曲")

        lu_map = {"甲": 2, "乙": 3, "丙": 5, "丁": 6, "戊": 5,
                  "己": 6, "庚": 8, "辛": 9, "壬": 11, "癸": 0}
        lu_idx = lu_map[self.year_gan]
        self.palaces[self.zhi_list[lu_idx]]["stars"].append("祿存")
        self.palaces[self.zhi_list[(lu_idx + 1) % 12]]["stars"].append("擎羊")
        self.palaces[self.zhi_list[(lu_idx - 1) % 12]]["stars"].append("陀羅")

        # 天魁 / 天鉞 (年干起)
        kui_yue = {"甲": (1, 7), "戊": (1, 7), "庚": (1, 7),
                   "乙": (0, 8), "己": (0, 8),
                   "丙": (11, 9), "丁": (11, 9),
                   "辛": (2, 6),
                   "壬": (3, 5), "癸": (3, 5)}
        kui_idx, yue_idx = kui_yue[self.year_gan]
        self.palaces[self.zhi_list[kui_idx]]["stars"].append("天魁")
        self.palaces[self.zhi_list[yue_idx]]["stars"].append("天鉞")

        year_zhi_idx = self._get_index(self.year_zhi, self.zhi_list)
        huo_start, ling_start = 0, 0
        if year_zhi_idx in [2, 6, 10]:
            huo_start, ling_start = 1, 3
        elif year_zhi_idx in [8, 0, 4]:
            huo_start, ling_start = 2, 10
        elif year_zhi_idx in [5, 9, 1]:
            huo_start, ling_start = 3, 10
        elif year_zhi_idx in [11, 3, 7]:
            huo_start, ling_start = 9, 10
        self.palaces[self.zhi_list[(huo_start + hour_idx) % 12]]["stars"].append("火星")
        self.palaces[self.zhi_list[(ling_start + hour_idx) % 12]]["stars"].append("鈴星")
        # 天空: 太歲前一位 (年支 + 1)
        year_zhi_idx_local = self._get_index(self.year_zhi, self.zhi_list)
        self.palaces[self.zhi_list[(year_zhi_idx_local + 1) % 12]]["stars"].append("天空")
        # 地劫: 從亥宮起子時順行
        self.palaces[self.zhi_list[(11 + hour_idx) % 12]]["stars"].append("地劫")

    def _arrange_misc_stars(self):
        year_zhi_idx = self._get_index(self.year_zhi, self.zhi_list)
        # 天馬: 採「月馬」(月支三合馬位) — 寅午戌→申, 申子辰→寅, 巳酉丑→亥, 亥卯未→巳
        month_zhi_idx = self._get_index(self.month_zhi, self.zhi_list)
        tian_ma_map = {2: 8, 6: 8, 10: 8, 8: 2, 0: 2, 4: 2,
                       5: 11, 9: 11, 1: 11, 11: 5, 3: 5, 7: 5}
        self.palaces[self.zhi_list[tian_ma_map.get(month_zhi_idx, 8)]]["stars"].append("天馬")

        # 天姚: 從丑宮起正月順行至生月
        month_val = self.lunar.getMonth()
        self.palaces[self.zhi_list[(1 + month_val - 1) % 12]]["stars"].append("天姚")
        # 天刑: 從酉宮起正月順行至生月
        self.palaces[self.zhi_list[(9 + month_val - 1) % 12]]["stars"].append("天刑")

        hong_luan_idx = (3 - year_zhi_idx) % 12
        self.palaces[self.zhi_list[hong_luan_idx]]["stars"].append("紅鸞")
        self.palaces[self.zhi_list[(hong_luan_idx + 6) % 12]]["stars"].append("天喜")

        gu_chen_map = {(2, 3, 4): 5, (5, 6, 7): 8, (8, 9, 10): 11, (11, 0, 1): 2}
        gua_su_map = {(2, 3, 4): 1, (5, 6, 7): 4, (8, 9, 10): 7, (11, 0, 1): 10}
        for k, v in gu_chen_map.items():
            if year_zhi_idx in k:
                self.palaces[self.zhi_list[v]]["stars"].append("孤辰")
                break
        for k, v in gua_su_map.items():
            if year_zhi_idx in k:
                self.palaces[self.zhi_list[v]]["stars"].append("寡宿")
                break

    def _arrange_birth_si_hua(self):
        si_hua_rules = self.sect.get_si_hua_rules()
        hua_types = ["祿", "權", "科", "忌"]
        stars = si_hua_rules[self.year_gan]
        for i, star in enumerate(stars):
            hua = hua_types[i]
            for zhi, data in self.palaces.items():
                clean_stars = [s.split('(')[0] for s in data["stars"]]
                if star in clean_stars:
                    if star in data["stars"]:
                        data["stars"].remove(star)
                    data["stars"].append(f"{star}({hua})")
                    break

    def _calculate_flying_stars(self):
        si_hua_rules = self.sect.get_si_hua_rules()
        hua_types = ["祿", "權", "科", "忌"]
        for zhi, data in self.palaces.items():
            gan = data["gan"]
            if gan not in si_hua_rules:
                continue
            stars_to_fly = si_hua_rules[gan]
            for i, star in enumerate(stars_to_fly):
                hua = hua_types[i]
                for target_zhi, target_data in self.palaces.items():
                    clean_stars = [s.split('(')[0] for s in target_data["stars"]]
                    if star in clean_stars:
                        data["si_hua_out"].append(
                            {"target_zhi": target_zhi, "star": star, "hua": hua}
                        )
                        target_data["si_hua_in"].append(
                            {"source_zhi": zhi, "star": star, "hua": hua}
                        )
                        break

    def _generate_analysis(self):
        report = []
        ming_palace = self.palaces[self.ming_zhi]
        main_stars = [s for s in ming_palace["stars"] if "(" not in s and len(s) == 2]
        if main_stars:
            report.append(f"【命宮主星】: {', '.join(main_stars)}")
        for fly in ming_palace["si_hua_out"]:
            target_name = self.palaces[fly["target_zhi"]]["name"].split("(")[0]
            interp = self.sect.get_interpretation("本命", fly['hua'], target_name, fly['star'])
            report.append(interp)
        return report

    def get_da_xian(self, current_age):
        ming_idx = self._get_index(self.ming_zhi, self.zhi_list)
        yang_gan = ["甲", "丙", "戊", "庚", "壬"]
        is_yang_year = self.year_gan in yang_gan
        is_male = self.gender == "男"
        # 陽男陰女順行,陰男陽女逆行
        direction = 1 if (is_yang_year == is_male) else -1
        da_xian_num = (current_age - self.ju_num) // 10
        if da_xian_num < 0:
            return None, None
        da_xian_idx = (ming_idx + da_xian_num * direction) % 12
        da_xian_zhi = self.zhi_list[da_xian_idx]
        da_xian_gan = self.palaces[da_xian_zhi]["gan"]
        return da_xian_zhi, da_xian_gan

    def get_liu_nian(self, year):
        solar = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
        return solar.getLunar().getYearZhi()

    def get_si_hua_for_gan(self, gan):
        return self.sect.get_si_hua_rules().get(gan, [])

    def get_da_xian_palace_names(self, da_xian_zhi):
        names = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄",
                 "遷移", "交友", "官祿", "田宅", "福德", "父母"]
        dx_ming_idx = self._get_index(da_xian_zhi, self.zhi_list)
        result = {}
        for i, name in enumerate(names):
            target_idx = (dx_ming_idx - i) % 12
            result[self.zhi_list[target_idx]] = name
        return result

    def get_liu_nian_palace_names(self, liu_nian_zhi):
        """流年視角下,各地支宮對應的宮名(流命/流兄/流夫...)"""
        names = ["命", "兄", "夫", "子", "財", "疾",
                 "遷", "友", "官", "田", "福", "父"]
        ln_ming_idx = self._get_index(liu_nian_zhi, self.zhi_list)
        result = {}
        for i, name in enumerate(names):
            target_idx = (ln_ming_idx - i) % 12
            result[self.zhi_list[target_idx]] = name
        return result

    def get_da_xian_palace_short(self, da_xian_zhi):
        """大限視角短名(大命/大兄/大夫...)"""
        names = ["命", "兄", "夫", "子", "財", "疾",
                 "遷", "友", "官", "田", "福", "父"]
        dx_ming_idx = self._get_index(da_xian_zhi, self.zhi_list)
        result = {}
        for i, name in enumerate(names):
            target_idx = (dx_ming_idx - i) % 12
            result[self.zhi_list[target_idx]] = name
        return result

    def get_da_xian_age_range(self, da_xian_zhi):
        """回傳該大限的虛歲區間 (start_age, end_age)。找不到回 None。"""
        ming_idx = self._get_index(self.ming_zhi, self.zhi_list)
        yang_gan = ["甲", "丙", "戊", "庚", "壬"]
        is_yang_year = self.year_gan in yang_gan
        is_male = self.gender == "男"
        direction = 1 if (is_yang_year == is_male) else -1
        target_idx = self._get_index(da_xian_zhi, self.zhi_list)
        # da_xian_num such that (ming_idx + da_xian_num*direction) % 12 == target_idx
        for n in range(12):
            if (ming_idx + n * direction) % 12 == target_idx:
                start = self.ju_num + n * 10
                return start, start + 9
        return None


# --- 3. Streamlit 介面 ---

st.set_page_config(page_title="欽天紫微斗數排盤(DST 支援版)", layout="wide")
st.title("🔮 欽天派紫微斗數智能排盤系統(支援 DST 自動校正)")

with st.sidebar:
    st.header("設定")
    selected_sect = st.selectbox("選擇流派", ["欽天門", "三合派"], index=0)

    st.markdown("---")
    st.header("輸入出生資料")
    year = st.number_input("西元年", min_value=1900, max_value=2100, value=1990)
    month = st.number_input("月", min_value=1, max_value=12, value=5)
    day = st.number_input("日", min_value=1, max_value=31, value=15)
    hour = st.number_input("時 (0-23)", min_value=0, max_value=23, value=10)
    minute = st.number_input("分 (0-59)", min_value=0, max_value=59, value=0)
    gender = st.selectbox("性別", ["男", "女"])

    timezone_options = list(TZ_STANDARD_LONGITUDE.keys())
    selected_timezone = st.selectbox("出生地時區", timezone_options, index=0)

    longitude_map = {
        "Asia/Taipei": 121.5, "Asia/Shanghai": 121.4, "Asia/Hong_Kong": 114.1,
        "Asia/Tokyo": 139.7, "America/New_York": -74.0,
        "America/Los_Angeles": -118.2, "America/Chicago": -87.6,
        "Europe/London": -0.1, "Europe/Paris": 2.3, "Europe/Berlin": 13.4,
        "Australia/Sydney": 151.2, "Pacific/Auckland": 174.7,
    }
    default_lon = longitude_map.get(selected_timezone, 120.0)
    longitude = st.number_input(
        "出生地經度(可微調)",
        value=default_lon,
        help="台北 121.5｜台中 120.68｜高雄 120.30｜台南 120.21｜新竹 120.97｜花蓮 121.61"
    )

    if 'prev_sect' not in st.session_state:
        st.session_state.prev_sect = selected_sect
    if st.session_state.prev_sect != selected_sect:
        st.session_state.pop('chart', None)
        st.session_state.prev_sect = selected_sect

    if st.button("開始排盤"):
        try:
            chart = QintianZiweiGold(
                year, month, day, hour, minute, gender,
                longitude, sect_name=selected_sect, timezone_str=selected_timezone
            )
            st.session_state['chart'] = chart
            st.success(f"✅ 排盤成功!使用流派:[{selected_sect}]")

            with st.expander("⏱️ 時間校正詳情", expanded=False):
                std_lon = TZ_STANDARD_LONGITUDE.get(selected_timezone, 120.0)
                dst_text = "已實施(夏令時間)" if chart.dst_active else "未實施(標準時間)"
                st.markdown(
                    f"- **輸入時間**: {year}/{month}/{day} {hour:02d}:{minute:02d} "
                    f"({selected_timezone})\n"
                    f"- **DST 狀態**: {dst_text}\n"
                    f"- **時區標準經線**: {std_lon}°\n"
                    f"- **經度時差**: {(longitude - std_lon) * 4:.1f} 分鐘\n"
                    f"- **最終真太陽時**: **{chart.solar_time.strftime('%Y-%m-%d %H:%M')}**"
                )
        except Exception as e:
            st.error(f"❌ 發生錯誤: {e}")


if 'chart' in st.session_state:
    chart = st.session_state['chart']

    st.sidebar.markdown("---")
    st.sidebar.header("🔮 運勢查詢")
    query_year = st.sidebar.number_input("查詢年份(西元)", min_value=1900, max_value=2100, value=2024)
    current_age = query_year - chart.solar.getYear() + 1

    da_xian_zhi, da_xian_gan = chart.get_da_xian(current_age)
    liu_nian_zhi = chart.get_liu_nian(query_year)

    da_xian_hua_stars = chart.get_si_hua_for_gan(da_xian_gan) if da_xian_gan else []
    liu_nian_gan = Solar.fromYmdHms(query_year, 1, 1, 0, 0, 0).getLunar().getYearGan()
    liu_nian_hua_stars = chart.get_si_hua_for_gan(liu_nian_gan)

    use_da_xian_view = st.sidebar.checkbox("啟用大限視角(旋轉盤面)", value=False)

    if use_da_xian_view and da_xian_zhi:
        palace_name_map = chart.get_da_xian_palace_names(da_xian_zhi)
        view_title = f"大限視角({da_xian_zhi}宮為命)"
    else:
        palace_name_map = {zhi: chart.palaces[zhi]["name"] for zhi in chart.zhi_list}
        view_title = "本命視角"

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("基本資訊")
        st.write(f"**流派**: {chart.sect.name}")
        st.write(f"**陽曆**: {chart.solar.toFullString()}")
        st.write(f"**農曆**: {chart.lunar.toString()}")
        st.write(f"**五行局**: {chart.wuxing_ju}")
        st.write(f"**命宮**: {chart.ming_zhi}, **身宮**: {chart.shen_zhi}")

        st.markdown("---")
        st.subheader(f"📅 {query_year}年 運勢分析")
        st.write(f"**虛歲**: {current_age} 歲")

        if da_xian_zhi:
            st.success(f"**大限命宮**: {da_xian_zhi}宮 ({da_xian_gan}{da_xian_zhi})")
            st.markdown("**大限四化重點:**")
            for i, star in enumerate(da_xian_hua_stars):
                hua = ['祿', '權', '科', '忌'][i]
                for zhi, data in chart.palaces.items():
                    clean_stars = [s.split('(')[0] for s in data["stars"]]
                    if star in clean_stars:
                        target_name = palace_name_map[zhi].split("(")[0]
                        interp = chart.sect.get_interpretation("大限", hua, target_name, star)
                        st.caption(f"• {interp}")
                        break
        else:
            st.warning("尚未起運")

        st.info(f"**流年命宮**: {liu_nian_zhi}宮")
        st.markdown("**流年四化重點:**")
        for i, star in enumerate(liu_nian_hua_stars):
            hua = ['祿', '權', '科', '忌'][i]
            for zhi, data in chart.palaces.items():
                clean_stars = [s.split('(')[0] for s in data["stars"]]
                if star in clean_stars:
                    target_name = palace_name_map[zhi].split("(")[0]
                    interp = chart.sect.get_interpretation("流年", hua, target_name, star)
                    st.caption(f"• {interp}")
                    break

    with col2:
        st.subheader(f"十二宮盤面({view_title})")

        # 主星集合(用來判斷是否粗體黑字)
        MAIN_STARS = {"紫微", "天機", "太陽", "武曲", "天同", "廉貞",
                      "天府", "太陰", "貪狼", "巨門", "天相", "天梁",
                      "七殺", "破軍"}

        # 宮名簡稱對照(本命視角)
        NAME_SHORT = {
            "命宮": "命", "兄弟": "兄", "夫妻": "夫", "子女": "子",
            "財帛": "財", "疾厄": "疾", "遷移": "遷", "交友": "友",
            "官祿": "官", "田宅": "田", "福德": "福", "父母": "父",
        }

        liu_nian_short = chart.get_liu_nian_palace_names(liu_nian_zhi)
        da_xian_short = chart.get_da_xian_palace_short(da_xian_zhi) if da_xian_zhi else {}

        # 來因宮: 年干在十二宮位中的位置(以宮干為準)
        lai_yin_zhi = None
        for zhi, p in chart.palaces.items():
            if p["gan"] == chart.year_gan:
                lai_yin_zhi = zhi
                break

        st.markdown("""
<style>
.lifedna-wrap { font-family: "Microsoft JhengHei", "PingFang TC", "Noto Sans TC", sans-serif; }
.lifedna-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    grid-template-rows: repeat(4, minmax(160px, auto));
    gap: 0;
    border: 2px solid #333;
    background: #fff;
}
.palace {
    border: 1px solid #bbb;
    position: relative;
    display: flex;
    flex-direction: column;
    background: #fff;
    min-height: 160px;
    overflow: hidden;
}
.palace.dx-ming { background: #FFE4E1; }
.palace.ln-ming { box-shadow: inset 0 0 0 3px #D32F2F; }
.palace .corner-dx {
    position: absolute; top: 2px; left: 2px;
    background: #2E7D32; color: #fff; font-size: 10px;
    padding: 1px 4px; border-radius: 2px; font-weight: bold; z-index: 2;
}
.palace .corner-ln {
    position: absolute; top: 2px; right: 2px;
    background: #D32F2F; color: #fff; font-size: 10px;
    padding: 1px 4px; border-radius: 2px; font-weight: bold; z-index: 2;
}
.palace .lai-yin {
    position: absolute; top: 18px; left: 2px;
    writing-mode: vertical-rl; -webkit-writing-mode: vertical-rl;
    color: #2E7D32; font-size: 11px; font-weight: bold;
    letter-spacing: 1px; z-index: 2;
}
.stars-area {
    flex: 1;
    display: flex;
    flex-direction: row-reverse;
    justify-content: flex-start;
    padding: 6px 6px 4px 18px;
    gap: 4px;
    align-items: flex-start;
}
.star-col {
    writing-mode: vertical-rl;
    -webkit-writing-mode: vertical-rl;
    text-orientation: upright;
    -webkit-text-orientation: upright;
    display: flex;
    flex-direction: column;
    align-items: center;
    line-height: 1.15;
    font-size: 14px;
}
.star-main { color: #000; font-weight: bold; }
.star-aux  { color: #444; font-weight: normal; font-size: 13px; }
.hua-badge {
    display: inline-block;
    writing-mode: horizontal-tb;
    -webkit-writing-mode: horizontal-tb;
    text-orientation: mixed;
    font-size: 10px;
    width: 14px; height: 14px; line-height: 14px;
    border-radius: 50%;
    color: #fff; font-weight: bold;
    margin-top: 2px;
    text-align: center;
}
.hua-quan { background: #D32F2F; }   /* 權 */
.hua-ji   { background: #1A237E; }   /* 忌 */
.hua-lu   { background: #2E7D32; }   /* 祿 */
.hua-ke   { background: #4FC3F7; }   /* 科 */
.palace-footer {
    border-top: 1px solid #ccc;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr 1.4fr;
    font-size: 11px;
    text-align: center;
    background: #fafafa;
}
.palace-footer > div {
    padding: 3px 2px;
    border-right: 1px solid #e0e0e0;
    line-height: 1.3;
}
.palace-footer > div:last-child { border-right: none; }
.foot-ganzhi { color: #000; font-weight: bold; }
.foot-name   { color: #7B3F99; font-weight: bold; font-size: 12px; }
.foot-age    { color: #666; }
.foot-tag    { color: #D32F2F; font-weight: bold; font-size: 10px; }

/* 中央資訊卡 */
.center-card {
    grid-column: 2 / span 2;
    grid-row: 2 / span 2;
    border: 1px solid #bbb;
    background: #FFF8E1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    padding: 12px;
    font-size: 13px;
    line-height: 1.7;
}
.center-card .name { font-size: 16px; font-weight: bold; color: #1B2A4A; margin-bottom: 4px; }
.center-card .ju { color: #7B3F99; font-weight: bold; margin-bottom: 6px; }
.center-card .liunian-tag {
    margin-top: 8px; background: #D32F2F; color: #fff;
    padding: 4px 10px; border-radius: 4px; font-weight: bold;
}

@media (max-width: 768px) {
    .lifedna-grid { grid-template-columns: repeat(2, 1fr); grid-template-rows: auto; }
    .center-card { grid-column: 1 / span 2; grid-row: auto; }
    .palace { min-height: 140px; }
}
</style>
""", unsafe_allow_html=True)

        # 4x4 layout: 12 宮位 + 中央(2x2)資訊卡
        # row, col (1-indexed grid positions)
        layout_positions = [
            ("巳", 1, 1), ("午", 1, 2), ("未", 1, 3), ("申", 1, 4),
            ("辰", 2, 1),                                  ("酉", 2, 4),
            ("卯", 3, 1),                                  ("戌", 3, 4),
            ("寅", 4, 1), ("丑", 4, 2), ("子", 4, 3), ("亥", 4, 4),
        ]

        def render_star_col(stars_in_col):
            """render 一個直書 column,內容為從上到下的星曜列表"""
            html = '<div class="star-col">'
            for star_str in stars_in_col:
                base = star_str.split('(')[0]
                hua = ''
                if '(' in star_str:
                    hua = star_str.split('(')[1].replace(')', '')
                cls = 'star-main' if base in MAIN_STARS else 'star-aux'
                html += f'<span class="{cls}">{base}</span>'
                if hua:
                    hua_cls = {
                        '權': 'hua-quan', '忌': 'hua-ji',
                        '祿': 'hua-lu', '科': 'hua-ke'
                    }.get(hua, 'hua-quan')
                    html += f'<span class="hua-badge {hua_cls}">{hua}</span>'
            html += '</div>'
            return html

        def render_palace(zhi):
            p = chart.palaces[zhi]
            classes = ["palace"]
            if zhi == da_xian_zhi:
                classes.append("dx-ming")
            if zhi == liu_nian_zhi:
                classes.append("ln-ming")

            stars = p['stars']
            # 將星曜分欄: 主星優先單獨成列,輔星可拼列。簡單策略:每 1-2 顆一列。
            # 為求顯示穩定:主星各自一列(含化曜),其他星依序每 2 顆一列。
            cols = []
            buffer_aux = []
            for s in stars:
                base = s.split('(')[0]
                if base in MAIN_STARS:
                    if buffer_aux:
                        cols.append(buffer_aux)
                        buffer_aux = []
                    cols.append([s])
                else:
                    buffer_aux.append(s)
                    if len(buffer_aux) >= 3:
                        cols.append(buffer_aux)
                        buffer_aux = []
            if buffer_aux:
                cols.append(buffer_aux)

            stars_html = '<div class="stars-area">'
            for c in cols:
                stars_html += render_star_col(c)
            stars_html += '</div>'

            # footer
            ganzhi = f"{p['gan']}{zhi}"
            dynamic_name = palace_name_map[zhi]
            base_name = dynamic_name.replace("(身)", "")
            short_name = NAME_SHORT.get(base_name, base_name[:1] if base_name else "")
            shen_mark = "(身)" if "(身)" in dynamic_name else ""
            name_disp = f"{short_name}{shen_mark}"

            age_range = chart.get_da_xian_age_range(zhi)
            if age_range:
                age_text = f"{age_range[0]}-{age_range[1]}"
            else:
                age_text = "-"

            # 流大標籤: 流年宮名 + 大限對應宮名
            ln_n = liu_nian_short.get(zhi, "")
            dx_n = da_xian_short.get(zhi, "")
            if ln_n and dx_n:
                tag_text = f"流{ln_n}大{dx_n}"
            elif ln_n:
                tag_text = f"流{ln_n}"
            elif dx_n:
                tag_text = f"大{dx_n}"
            else:
                tag_text = ""

            footer_html = (
                f'<div class="palace-footer">'
                f'<div class="foot-ganzhi">{ganzhi}</div>'
                f'<div class="foot-name">{name_disp}</div>'
                f'<div class="foot-age">{age_text}</div>'
                f'<div class="foot-tag">{tag_text}</div>'
                f'</div>'
            )

            corner_html = ""
            if zhi == da_xian_zhi:
                corner_html += '<div class="corner-dx">大命</div>'
            if zhi == liu_nian_zhi:
                corner_html += '<div class="corner-ln">流命</div>'
            if zhi == lai_yin_zhi:
                corner_html += '<div class="lai-yin">來因宮</div>'

            return (
                f'<div class="{" ".join(classes)}" '
                f'style="grid-row:{layout_zhi_to_pos[zhi][0]};grid-column:{layout_zhi_to_pos[zhi][1]};">'
                f'{corner_html}{stars_html}{footer_html}'
                f'</div>'
            )

        layout_zhi_to_pos = {z: (r, c) for z, r, c in layout_positions}

        # 中央資訊卡
        try:
            solar_full = chart.solar.toFullString()
        except Exception:
            solar_full = f"{chart.solar.getYear()}-{chart.solar.getMonth():02d}-{chart.solar.getDay():02d}"
        try:
            lunar_str = chart.lunar.toString()
        except Exception:
            lunar_str = ""
        gender_text = f"{chart.wuxing_ju}{'陽' if chart.year_gan in ['甲','丙','戊','庚','壬'] else '陰'}{chart.gender}"
        center_html = (
            f'<div class="center-card">'
            f'<div class="name">命主</div>'
            f'<div class="ju">{gender_text}</div>'
            f'<div>陽曆 {solar_full}</div>'
            f'<div>農曆 {lunar_str}</div>'
            f'<div style="margin-top:6px;">命宮 <b>{chart.ming_zhi}</b>　身宮 <b>{chart.shen_zhi}</b></div>'
            f'<div class="liunian-tag">{current_age}歲　{query_year} {liu_nian_gan}{liu_nian_zhi}年</div>'
            f'</div>'
        )

        html_grid = '<div class="lifedna-wrap"><div class="lifedna-grid">'
        for zhi, _, _ in layout_positions:
            html_grid += render_palace(zhi)
        html_grid += center_html
        html_grid += '</div></div>'
        st.markdown(html_grid, unsafe_allow_html=True)

        st.caption("圖例: 淡紅底=大限命宮(大命) | 紅框=流年命宮(流命) | 綠字「來因宮」=年干所在宮 | 化權紅・化忌深藍・化祿綠・化科淺藍")
