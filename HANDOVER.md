# HANDOVER.md — 2026-03-22 セッション引き継ぎ

**作成日**: 2026-03-22
**デスクトップ版**: v9.9.0（`main`ブランチ）
**Web版**: daihon-rakku-web（Railway + Cloudflare Pages）

---

## 1. 2026-03-22 セッション成果

### Cloudflare Pages本番化
- [x] ログインエラー修正（`.env.production` 追加 — ビルド時に環境変数がインライン化されない問題）
- [x] CORS修正（Railway `ALLOWED_ORIGINS` に `https://daihon-rakku-web.pages.dev` 追加）
- [x] Supabase Auth redirect URL設定（Site URL + Redirect URLs）
- [x] 10シーン生成テスト成功（全シーン生成・エクスポート確認済み）

### モデルID更新
- [x] Sonnet: `claude-sonnet-4-20250514` → `claude-sonnet-4-6`（同額$3/$15、性能向上）
- [x] Opus: `claude-opus-4-20250918`(無効ID) → `claude-opus-4-6`（$15/$75→$5/$25）
- [x] Opus清書パス有効化（intensity≥5シーン対象）
- [x] Haiku 4.5 / Haiku 3(fast) は据え置き（※Haiku 3は2026/4/19廃止予定）

### JWT認証強化
- [x] 3段階フォールバック（PyJWKClient → httpx直接JWKS取得 → HS256レガシー）
- [x] HTTPException握りつぶしバグ修正（try/except/elseパターン）
- [x] JWKSキャッシュにTTL(1時間)追加
- [x] エラー詳細の非露出化（汎用メッセージに統一）

### 法的ページ整合
- [x] 利用規約のクレジット有効期限を特商法と統一（「期限なし・解約まで繰越」）

### 関連コミット
| # | 内容 | コミット |
|---|------|---------|
| 1 | .env.production追加（ビルド時env var） | `f3654e1` |
| 2 | モデルID更新+Opus清書有効化 | `a1ba108` |
| 3 | モデルID修正（日付サフィックス不要） | `f862833` |
| 4 | JWT認証3段階フォールバック | `d51f12a` |
| 5 | JWT認証の重大問題3件修正 | `3bf5a14` |
| 6 | 利用規約クレジット有効期限統一 | `6ec6818` |

---

## 2. 現在の状態

### インフラ
| サービス | 状態 | 備考 |
|---------|------|------|
| **Railway (API)** | zoological-tranquility / Online | Hobby $3.40残（要Pro移行） |
| **Cloudflare Pages** | daihon-rakku-web.pages.dev / **正常稼働** | ログイン・生成・エクスポート全て動作確認済み |
| **Vercel** | daihon-rakku-web.vercel.app / Online | 念のため残存（無料、削除不要） |
| **Upstash Redis** | **削除済み** | コード・サービスとも完全除去 |
| **Railway Worker** | **削除済み** | Huey廃止済み |
| **Supabase** | Free tier | user_profiles/generation_jobs等 |
| **Stripe** | **本番審査中**（2026-03-22申請） | 審査通過後に本番切替 |

### Cloudflare Pages設定
- Build command: `npm run build`
- Build output: `out`
- Root directory: `frontend`
- 環境変数: NEXT_PUBLIC_SUPABASE_URL / ANON_KEY / API_URL / STRIPE_KEY 設定済み
- `.env.production` をリポジトリにコミット済み（NEXT_PUBLIC_*は公開値）

### 使用モデル
| 用途 | モデルID | 料金 |
|------|---------|------|
| メイン生成(i≤3) | `claude-haiku-4-5-20251001` | $1/$5 |
| 高intensity(i≥4) | `claude-sonnet-4-6` | $3/$15 |
| Opus清書(i≥5) | `claude-opus-4-6` | $5/$25 |
| 軽量タスク | `claude-3-haiku-20240307` | $0.25/$1.25（⚠️4/19廃止予定） |

---

## 3. 次にやるべきステップ

### Stripe本番切替（審査通過後）
1. 本番APIキー取得（Secret Key / Publishable Key）
2. 本番用の商品・価格（Price ID）6つ作成（月額3プラン + 追加クレジット3種）
3. Webhookエンドポイント設定
4. Railway環境変数更新（STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, 各STRIPE_PRICE_*）
5. Cloudflare Pages環境変数更新（NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY）→ 再ビルド

### 優先度高
6. **Railway残高** — $3.40のみ、Pro移行検討
7. **Haiku 3廃止対応** — 2026/4/19までに`haiku_fast`をHaiku 4.5に統一

### 優先度中
8. 品質確認（セリフ品質・Opus清書の効果検証）
9. エクスポート全形式動作確認

---

## 4. 重要なアカウント情報

| サービス | 情報 |
|---------|------|
| **Cloudflare** | K.75mixpc@gmail.com / daihon-rakku-web.pages.dev |
| **Railway** | zoological-tranquility（メインAPIのみ）/ ALLOWED_ORIGINSにpages.dev追加済み |
| **Vercel** | daihon-rakku-web.vercel.app（残存・無料） |
| **Supabase** | czkzaqyrkswvfylczwoz / ES256 JWT / user_profiles.plan CHECK制約に'admin'追加済み |
| **Stripe** | 本番審査中（2026-03-22申請） |

---

**合言葉「Stripe本番切替」で次のセッションを開始してください。**
