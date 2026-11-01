# -*- coding: utf-8 -*-
"""
BAO CAO NGAY CONG SC: ATC/ngay, thoi gian lam TB/ngay, ngay cong (ca ngay = 1, nua ngay = 0.5)
Doc BAOCAO.xlsx (sheet tudaunam) -> sinh:
  - bao_cao_ngay_cong.html  (dashboard tuong tac, mo truc tiep bang trinh duyet)
  - BAO_CAO_NGAY_CONG.xlsx  (bang tong hop de gui di)

Quy tac (sua o phan CAU HINH):
  * Chi tinh ca co checkin, tru ca 'Huy'. Moi ca = 1 luot ATC.
  * Ngay cua ca = ngay checkin.
  * Buoi sang: co checkin truoc 12:30. Buoi chieu: co checkin tu 13:00.
    Record checkin 12:30-13:00 la gio nghi trua (lam lo) -> khong tinh la buoi chieu.
  * Ngay co CA sang va chieu -> 1 cong; chi 1 buoi -> 0.5 cong.
      - ngoai le: 1 record keo dai tu sang sang chieu (checkout cuoi >= 13:30) van tinh 1 cong
  * Ma truong hop A-F ghi vao cot 'Truong hop' de doi chieu.
  * Thoi gian lam = tong cac khoang checkin->checkout da gop (khong tinh trung lap).
  * Ca loi du lieu (checkout khac ngay, hoac > 480 phut) van tinh 1 ATC nhung bo qua thoi luong.
"""
import json
import os
import sys
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'BAOCAO.xlsx')
OUT_HTML = os.path.join(BASE, 'bao_cao_ngay_cong.html')
OUT_XLSX = os.path.join(BASE, 'BAO_CAO_NGAY_CONG.xlsx')

# ===== CAU HINH =====
SPLIT_MIN = 12 * 60 + 30      # 12:30 - het buoi sang (record checkin truoc 12:30 la buoi sang)
AFTERNOON_CI_MIN = 13 * 60    # 13:00 - bat dau buoi chieu (12:30-13:00 la gio nghi trua, khong tinh)
AFTERNOON_CO_MIN = 13 * 60 + 30  # 1 record keo dai, checkout cuoi >= 13:30 coi nhu co buoi chieu
MAX_DUR_MIN = 480             # ca > 8h coi la loi nhap lieu


def hhmm(m):
    m = int(round(m))
    return '%02d:%02d' % (m // 60, m % 60)


def main():
    df = pd.read_excel(SRC, sheet_name='tudaunam')
    df['full'] = df['Người xử lý'].astype(str).str.strip()
    df['ma'] = df['full'].str.extract(r'^(\d+)')[0]
    df['ci'] = pd.to_datetime(df['Thời gian checkin'], errors='coerce')
    df['co'] = pd.to_datetime(df['Thời gian checkout'], errors='coerce')
    df = df[df['ci'].notna() & (df['Tình trạng xử lý'] != 'Hủy') & df['ma'].notna()].copy()

    df['ngay'] = df['ci'].dt.normalize()
    same_day = df['co'].notna() & (df['co'].dt.normalize() == df['ngay'])
    dur = (df['co'] - df['ci']).dt.total_seconds() / 60
    df['valid'] = same_day & (dur >= 0) & (dur <= MAX_DUR_MIN)
    df['ci_m'] = df['ci'].dt.hour * 60 + df['ci'].dt.minute + df['ci'].dt.second / 60
    df['co_m'] = (df['co'].dt.hour * 60 + df['co'].dt.minute + df['co'].dt.second / 60).where(df['valid'], df['ci_m'])
    df['rid'] = df['Retailer ID']

    # thong tin SC
    meta = {}
    for ma, g in df.groupby('ma'):
        full = g['full'].iloc[-1]
        # lay ten day du, bo ma dau
        name = full.split(' - ', 1)[1] if ' - ' in full else full
        nghi = bool(g['full'].str.contains('Đã nghỉ').any())
        coacher = 'Coacher' in full
        meta[ma] = {'ma': ma, 'name': name.replace(' - Đã nghỉ', ''), 'label': full.replace(' - Đã nghỉ', ''),
                    'nghi': nghi, 'coacher': coacher}

    rows = []
    for (ma, ngay), g in df.groupby(['ma', 'ngay']):
        g = g.sort_values('ci_m')
        n = len(g)
        gv = g[g['valid']]
        # gop khoang thoi gian
        work = 0.0
        cur_s = cur_e = None
        for s, e in zip(gv['ci_m'], gv['co_m']):
            if cur_s is None:
                cur_s, cur_e = s, e
            elif s <= cur_e:
                cur_e = max(cur_e, e)
            else:
                work += cur_e - cur_s
                cur_s, cur_e = s, e
        if cur_s is not None:
            work += cur_e - cur_s
        first_ci = g['ci_m'].min()
        last_co = g['co_m'].max()
        span = (gv['co_m'].max() - gv['ci_m'].min()) if len(gv) else 0.0
        has_m = first_ci < SPLIT_MIN
        has_a_ci = (g['ci_m'] >= AFTERNOON_CI_MIN).any()      # co record checkin tu 13:00
        has_a_co = last_co >= AFTERNOON_CO_MIN                  # hoac 1 record keo qua 13:30
        has_a = has_a_ci or has_a_co
        has_lunch = ((g['ci_m'] >= SPLIT_MIN) & (g['ci_m'] < AFTERNOON_CI_MIN)).any()
        cong = 1.0 if (has_m and has_a) else 0.5
        if has_m and has_a_ci:
            case = 'A'   # co record sang + record chieu rieng biet
        elif has_m and has_a_co:
            case = 'C'   # 1 record keo tu sang sang chieu
        elif has_m and has_lunch:
            case = 'B'   # lam lo sang gio nghi trua 12:30-13:00
        elif has_m and last_co >= SPLIT_MIN:
            case = 'D'   # chi sang, checkout cuoi qua 12:30
        elif has_m:
            case = 'E'   # chi buoi sang
        else:
            case = 'F'   # chi buoi chieu
        rows.append({
            'ma': ma, 'd': ngay.strftime('%Y-%m-%d'), 'n': int(n), 'nv': int(len(gv)),
            'kh': int(g['rid'].nunique()), 'w': round(work, 1), 's': round(float(span), 1),
            'fi': hhmm(first_ci), 'lo': hhmm(last_co), 'c': cong, 'case': case,
            'sang': bool(has_m), 'chieu': bool(has_a),
        })

    out = pd.DataFrame(rows)
    print('So dong SC-ngay:', len(out), '| Cong 1:', (out.c == 1).sum(), '| Cong 0.5:', (out.c == 0.5).sum())
    print('ATC/cong toan doi:', round(out.n.sum() / out.c.sum(), 2),
          '| Gio lam/cong:', round(out.w.sum() / 60 / out.c.sum(), 2))

    # ===== EXCEL =====
    out['thang'] = out['d'].str[:7]
    out['SC'] = out['ma'].map(lambda m: meta[m]['label'])
    out['trang_thai'] = out['ma'].map(lambda m: 'Đã nghỉ' if meta[m]['nghi'] else 'Đang làm')

    def summ(g):
        cong = g['c'].sum()
        nv = g['nv'].sum()
        return pd.Series({
            'Ngày có mặt': len(g),
            'Ngày công': cong,
            'Ngày cả ngày (1 công)': int((g['c'] == 1).sum()),
            'Ngày nửa buổi (0.5 công)': int((g['c'] == 0.5).sum()),
            'Tổng ATC': int(g['n'].sum()),
            'ATC / ngày công': round(g['n'].sum() / cong, 2),
            'Giờ làm TB / ngày công': round(g['w'].sum() / 60 / cong, 2),
            'Phút TB / ATC': round(g['w'].sum() / nv, 1) if nv else None,
            'Giờ TB checkin→checkout / ngày': round(g['s'].mean() / 60, 2),
        })

    by_sc = out.groupby('SC').apply(summ, include_groups=False).reset_index()
    label_nghi = {m['label']: m['nghi'] for m in meta.values()}
    by_sc['Trạng thái'] = by_sc['SC'].map(lambda s: 'Đã nghỉ' if label_nghi.get(s) else 'Đang làm')
    by_sc = by_sc.sort_values('ATC / ngày công', ascending=False)
    by_m = out.groupby(['thang', 'SC']).apply(summ, include_groups=False).reset_index().rename(columns={'thang': 'Tháng'})
    CASE_DESC = {
        'A': 'A - Có record sáng + record chiều (từ 13:00)',
        'B': 'B - Chỉ sáng, làm lố sang 12:30-13:00 (0.5)',
        'C': 'C - 1 record kéo dài sáng sang chiều (checkout >= 13:30)',
        'D': 'D - Chỉ sáng, checkout cuối qua 12:30 (0.5)',
        'E': 'E - Chỉ buổi sáng (0.5)',
        'F': 'F - Chỉ buổi chiều (0.5)',
    }
    case_by_key = {(r['ma'], r['d']): CASE_DESC[r['case']] for r in rows}
    out['truong_hop'] = [case_by_key[(m, d)] for m, d in zip(out['ma'], out['d'])]
    detail = out[['d', 'SC', 'trang_thai', 'n', 'kh', 'fi', 'lo', 'w', 's', 'c', 'truong_hop']].rename(columns={
        'd': 'Ngày', 'trang_thai': 'Trạng thái', 'n': 'Số ATC', 'kh': 'Số KH', 'fi': 'Checkin đầu',
        'lo': 'Checkout cuối', 'w': 'Phút làm việc', 's': 'Phút checkin→checkout', 'c': 'Ngày công',
        'truong_hop': 'Trường hợp'}).sort_values(['Ngày', 'SC'])

    try:
        with pd.ExcelWriter(OUT_XLSX, engine='openpyxl') as xw:
            by_sc.to_excel(xw, sheet_name='Tong_hop_SC', index=False)
            by_m.to_excel(xw, sheet_name='Theo_thang_SC', index=False)
            detail.to_excel(xw, sheet_name='Chi_tiet_theo_ngay', index=False)
            for ws in xw.book.worksheets:
                ws.freeze_panes = 'A2'
                for col in ws.columns:
                    w = max(len(str(c.value)) if c.value is not None else 0 for c in col[:60])
                    ws.column_dimensions[col[0].column_letter].width = min(max(10, w + 2), 48)
        print('Da ghi', OUT_XLSX)
    except Exception as ex:
        print('Khong ghi duoc Excel:', ex)

    # ===== HTML =====
    payload = {
        'sc': list(meta.values()),
        'rows': [{k: r[k] for k in ('ma', 'd', 'n', 'nv', 'kh', 'w', 's', 'fi', 'lo', 'c', 'case')} for r in rows],
        'cfg': {'split': hhmm(SPLIT_MIN), 'afternoonCi': hhmm(AFTERNOON_CI_MIN), 'afternoonCo': hhmm(AFTERNOON_CO_MIN), 'maxDur': MAX_DUR_MIN},
    }
    with open(os.path.join(BASE, 'bao_cao_ngay_cong.template.html'), 'r', encoding='utf-8') as f:
        tpl = f.read()
    html = tpl.replace('/*__DATA__*/null', json.dumps(payload, ensure_ascii=False, separators=(',', ':')))
    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print('Da ghi', OUT_HTML)


if __name__ == '__main__':
    main()
