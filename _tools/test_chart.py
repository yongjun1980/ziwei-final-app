"""Throwaway: verify 1980/7/21 04:00 男 台中 against LifeDNA reference."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# stub streamlit so app.py imports cleanly
class _Stub:
    def __getattr__(self, n): return _Stub()
    def __call__(self, *a, **k): return _Stub()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return iter([])
_stub = _Stub()
sys.modules['streamlit'] = _stub

from app import QintianZiweiGold

chart = QintianZiweiGold(1980, 7, 21, 4, 0, '男',
                        longitude=120.68, sect_name='欽天門',
                        timezone_str='Asia/Taipei')

print(f"五行局: {chart.wuxing_ju}")
print(f"命宮: {chart.ming_zhi} | 身宮: {chart.shen_zhi}")
print(f"真太陽時: {chart.solar_time}")
print()

expected = {
    '巳': ['天機(權)', '右弼', '天馬'],
    '午': ['紫微', '文曲', '天姚'],
    '未': ['陀羅', '天鉞', '紅鸞'],
    '申': ['破軍', '文昌', '祿存(權)'],
    '酉': ['天空', '左輔', '擎羊'],
    '戌': ['廉貞', '天府(忌)'],
    '亥': ['太陰(科)(祿)'],
    '子': ['貪狼', '鈴星(祿)'],
    '丑': ['天同', '巨門(忌)', '地劫', '天魁', '天喜'],
    '寅': ['武曲', '天相', '天刑(權)'],
    '卯': ['太陽', '天梁(祿)(科)'],
    '辰': ['七殺', '火星'],
}

zhi_order = ['巳','午','未','申','酉','戌','亥','子','丑','寅','卯','辰']
print(f"{'宮':3} {'實際':50} | 預期")
print("-" * 110)
mismatches = []
for z in zhi_order:
    actual = chart.palaces[z]['stars']
    exp = expected[z]
    # compare as sets of "main" names (strip 化)
    a_clean = sorted([s.split('(')[0] for s in actual])
    e_clean = sorted([s.split('(')[0] for s in exp])
    only_actual = set(a_clean) - set(e_clean)
    only_expected = set(e_clean) - set(a_clean)
    mark = '✓' if not only_actual and not only_expected else '✗'
    print(f"{z}  {','.join(actual):48} | {','.join(exp)}  {mark}")
    if only_actual or only_expected:
        mismatches.append((z, only_actual, only_expected))

print()
print("=" * 60)
if mismatches:
    print(f"❌ {len(mismatches)} palace(s) mismatch:")
    for z, oa, oe in mismatches:
        if oa: print(f"  {z}: extra {oa}")
        if oe: print(f"  {z}: missing {oe}")
else:
    print("✅ All 12 palaces match LifeDNA reference (main star names).")
