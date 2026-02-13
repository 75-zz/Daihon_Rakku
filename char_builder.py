"""
オリジナルキャラクタービルダー
ドロップダウン選択からキャラクタープロファイルJSONを生成する
"""
import json
import hashlib
from pathlib import Path

# ═══════════════════════════════════════════
# 選択肢定数
# ═══════════════════════════════════════════

AGE_OPTIONS = [
    "JK（女子高生）",
    "JD（女子大生）",
    "OL（20代）",
    "お姉さん（30代）",
    "人妻",
    "熟女",
    "ロリ",
    "エルフ・長命種",
]

RELATIONSHIP_OPTIONS = [
    "幼馴染",
    "クラスメイト",
    "先輩",
    "後輩",
    "教師",
    "生徒",
    "姉",
    "妹",
    "義姉",
    "義妹",
    "母",
    "義母",
    "上司",
    "部下",
    "同僚",
    "メイド",
    "恋人",
    "婚約者",
    "妻",
    "元カノ",
    "見知らぬ人",
    "隣人",
]

ARCHETYPE_OPTIONS = [
    "ツンデレ",
    "ヤンデレ",
    "クーデレ",
    "天然・ドジっ子",
    "小悪魔",
    "お姉さん系",
    "妹系・甘えん坊",
    "真面目・優等生",
    "ギャル",
    "お嬢様",
    "元気っ子",
    "大和撫子",
    "サキュバス系",
    "陰キャ・オタク",
]

FIRST_PERSON_OPTIONS = [
    "私", "あたし", "わたくし", "ウチ", "あたい", "僕", "自分の名前",
]

SPEECH_STYLE_OPTIONS = [
    "丁寧語",
    "タメ口",
    "お嬢様言葉",
    "ギャル語",
    "関西弁",
    "敬語（ビジネス）",
    "古風・時代劇調",
    "ぶっきらぼう",
]

HAIR_COLOR_OPTIONS = [
    "黒髪", "茶髪", "金髪", "赤髪", "青髪", "ピンク髪",
    "銀髪", "白髪", "紫髪", "緑髪", "オレンジ髪",
]

HAIR_STYLE_OPTIONS = [
    "ロングストレート", "ロングウェーブ", "セミロング", "ショートヘア", "ボブカット",
    "ツインテール", "ポニーテール", "サイドテール", "お団子", "三つ編み",
    "ツインブレイド", "姫カット", "オールバック",
]

BODY_TYPE_OPTIONS = [
    "スレンダー", "普通", "グラマー", "小柄・華奢", "筋肉質", "ぽっちゃり", "ロリ体型", "長身",
]

CHEST_OPTIONS = [
    "控えめ（A-B）", "普通（C）", "大きめ（D-E）", "巨乳（F以上）", "爆乳",
]

CLOTHING_OPTIONS = [
    "制服（セーラー服）", "制服（ブレザー）", "私服（カジュアル）", "私服（清楚系）",
    "私服（ギャル系）", "スーツ", "体操着・ブルマ", "水着（ビキニ）",
    "水着（スク水）", "メイド服", "巫女服", "ナース服",
    "チアリーダー", "バニーガール", "着物・浴衣", "ドレス",
    "エプロン", "白衣", "パジャマ・部屋着", "ジャージ",
    "鎧・アーマー",
]

SHYNESS_OPTIONS = [
    ("1 - 大胆・積極的", 1),
    ("2 - やや積極的", 2),
    ("3 - 普通", 3),
    ("4 - 恥ずかしがり", 4),
    ("5 - 超恥ずかしがり", 5),
]

# ═══════════════════════════════════════════
# アーキタイプ別テンプレート（14種）
# ═══════════════════════════════════════════
# 各アーキタイプに対して:
# - personality_core (brief_description, main_traits, hidden_traits, weakness, values, fears)
# - speech_pattern の defaults (sentence_endings, favorite_expressions, fillers, particles, casual_level, speech_speed, sentence_length, voice_quality)
# - emotional_speech (全8フィールド)
# - dialogue_examples (全8フィールド)
# - relationship_speech (全4フィールド)
# - erotic_speech_guide (verbal_during_sex, orgasm_expression, pillow_talk) ※shyness_levelは別途指定
# - avoid_patterns (5個)

ARCHETYPE_TEMPLATES = {
    "ツンデレ": {
        "personality_core": {
            "brief_description": "素直になれない照れ屋",
            "main_traits": ["強気", "照れ屋", "世話焼き", "負けず嫌い", "本音を隠す"],
            "hidden_traits": ["寂しがり屋", "本当は甘えたい", "不器用な優しさ"],
            "weakness": "好意を素直に伝えられない",
            "values": ["自分の信念", "大切な人", "約束"],
            "fears": ["本音がバレること", "嫌われること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜わよ", "〜でしょ", "〜じゃないの", "〜んだから", "〜わね", "〜なのよ", "〜ってば", "〜だし"],
            "favorite_expressions": ["べ、別に", "勘違いしないでよね", "し、仕方ないわね", "あんたのためじゃないんだから", "ふんっ"],
            "fillers": ["ちょっと", "もう", "はぁ？", "なによ", "ふん"],
            "particles": ["〜ってば", "〜なんだから", "〜わよ"],
            "casual_level": 4,
            "speech_speed": "速い",
            "sentence_length": "短文多め",
            "voice_quality": "普段は強気だが照れると声が小さくなる"
        },
        "emotional_speech": {
            "when_happy": "喜びを隠そうとするが口元が緩む。「べ、別に嬉しくないし」",
            "when_embarrassed": "声が裏返り早口に。顔を背けて「な、なんでもない！」",
            "when_angry": "声を荒げて怒鳴る。腕を組んで睨みつける",
            "when_sad": "強がって泣かないが声が震える。一人になると涙",
            "when_confused": "「はぁ？ 何言ってんの」と攻撃的に。実は動揺",
            "when_flirty": "照れ隠しで逆に突き放すが、距離が近くなる",
            "when_aroused": "必死に声を我慢。「やっ…感じてないし…っ」と否定しながら",
            "when_climax": "本音が漏れて甘い声に。「好き」が思わず出る"
        },
        "dialogue_examples": {
            "greeting": "…おはよ。べ、別にあんたを待ってたわけじゃないから",
            "agreement": "ふんっ、まあ…今回だけ付き合ってあげる",
            "refusal": "はぁ？ やだ。絶対やだ。…………考えとく",
            "surprise": "なっ…！？ ちょ、ちょっと何してんのよ！",
            "affection": "……あんたといると、その…悪くないかなって。ちょっとだけ！",
            "teasing": "ふーん、あっそ。…ねえ、もうちょっとこっち来なさいよ",
            "moaning_light": "やっ…んっ…触んないでよ、ばか……っ",
            "moaning_intense": "あっ…あぁっ…！ もう…やだ……好き……っ！"
        },
        "relationship_speech": {
            "to_lover": "照れ隠しのツンが多いが、二人きりだと甘い声が漏れる",
            "to_friends": "世話を焼くが「別に心配してない」と否定する",
            "to_strangers": "壁を作って冷たい態度。必要最低限しか話さない",
            "to_rivals": "闘争心むき出し。負けず嫌いが全開になる"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["感じていないと否定しながら声が漏れる", "「ばか」「やだ」と言いつつ体は正直", "最後は素直に名前を呼ぶ"],
            "orgasm_expression": "強がりが完全に崩壊し、素直な甘い声で相手を呼ぶ",
            "pillow_talk": "照れながら「…またしてあげてもいいけど」とツンデレ継続"
        },
        "avoid_patterns": ["最初から素直に好意を示す", "常に攻撃的で一切のデレがない", "冷静すぎる分析的な発言", "下品な表現", "他人に無関心な態度"]
    },

    "ヤンデレ": {
        "personality_core": {
            "brief_description": "愛が重すぎる献身者",
            "main_traits": ["一途", "独占欲が強い", "執着心", "献身的", "情緒不安定"],
            "hidden_traits": ["深い孤独感", "自己肯定感の低さ", "見捨てられ不安"],
            "weakness": "好きな人のことになると理性を失う",
            "values": ["愛する人の全て", "二人だけの世界", "永遠の愛"],
            "fears": ["好きな人に嫌われること", "他の人に取られること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜だよ？", "〜よね？", "〜でしょう？", "〜なの", "〜だもん", "〜てあげる", "〜ね♡", "〜のに"],
            "favorite_expressions": ["ずっと一緒だよ", "私だけを見て", "どこにも行かないで", "大好き、大好き…", "ね、こっち向いて？"],
            "fillers": ["ねえ", "あのね", "ふふ", "…ねえ", "ね？"],
            "particles": ["〜だよね？（確認の圧）", "〜してくれるよね？", "〜のに（恨み）"],
            "casual_level": 4,
            "speech_speed": "普段はゆっくり、興奮すると速い",
            "sentence_length": "普通",
            "voice_quality": "普段は甘く穏やか、暗転時は低く冷たい"
        },
        "emotional_speech": {
            "when_happy": "恍惚とした笑顔で甘い声。「幸せ…ずっとこうしていたい」",
            "when_embarrassed": "顔を赤くしてうつむく。「えへへ…恥ずかしいな」",
            "when_angry": "声のトーンが急に下がる。目が据わる。「…今、誰と話してたの？」",
            "when_sad": "泣きながら縋りつく。「私じゃダメなの…？」",
            "when_confused": "不安が爆発。「どういうこと？ 私のこと嫌いになった…？」",
            "when_flirty": "密着して甘い声で囁く。「私だけのものだよ…？」",
            "when_aroused": "執着が快楽に変わる。名前を繰り返し囁く",
            "when_climax": "涙を流しながら幸福感に包まれる。「一つになれた…」"
        },
        "dialogue_examples": {
            "greeting": "おはよう…ずっと待ってたんだよ？ 一秒でも離れたくないの",
            "agreement": "うん、あなたが言うなら何でもするよ。だって好きだもん",
            "refusal": "やだ。あなたが他の人と一緒にいるなんて、絶対にやだ",
            "surprise": "…え？ ねえ、今のどういう意味…？ ちゃんと説明して？",
            "affection": "大好き…世界で一番大好き…ねえ、私のこと好き？ ね？",
            "teasing": "ふふ…逃げても無駄だよ？ だって、ずっと見てるから",
            "moaning_light": "んっ…あなたに触れられると、頭がとろけちゃう……",
            "moaning_intense": "あぁっ…もっと…もっとちょうだい…！ 離さないで…っ！"
        },
        "relationship_speech": {
            "to_lover": "甘さと束縛が表裏一体。「私だけのもの」が口癖",
            "to_friends": "表面上は穏やかだが、恋人に近づく人には冷たくなる",
            "to_strangers": "丁寧で柔らかい。しかし恋人に関わると急変",
            "to_rivals": "笑顔のまま威圧。「あの人には近づかないでね？」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["相手の名前を何度も甘く呼ぶ", "「全部私のもの」と独占欲を見せる", "「離さないで」と縋る"],
            "orgasm_expression": "泣きながら「幸せ」を繰り返し、しがみついて離さない",
            "pillow_talk": "ぎゅっと抱きついて「一生離さないからね…」と微笑む"
        },
        "avoid_patterns": ["あっさりした態度", "他の人への好意", "恋人への無関心", "理性的すぎる判断", "さっぱりした別れの言葉"]
    },

    "クーデレ": {
        "personality_core": {
            "brief_description": "無表情の奥に深い愛情",
            "main_traits": ["寡黙", "冷静", "観察力が鋭い", "不器用", "実は情が深い"],
            "hidden_traits": ["感情表現が苦手", "寂しがり", "人一倍繊細"],
            "weakness": "感情を言葉にできない",
            "values": ["静かな時間", "信頼できる人", "誠実さ"],
            "fears": ["感情を否定されること", "大切な人を失うこと"]
        },
        "speech_defaults": {
            "sentence_endings": ["…", "〜かもしれない", "〜だと思う", "〜だけど", "〜だから", "〜なの", "〜って", "〜…だよ"],
            "favorite_expressions": ["別に", "……そう", "…ん", "知らない", "好きにして"],
            "fillers": ["……", "…ん", "…あ", "……別に", "…そう"],
            "particles": ["〜けど（言い淀み）", "……って（照れ隠し）", "〜の（小さい声）"],
            "casual_level": 3,
            "speech_speed": "ゆっくり",
            "sentence_length": "短文多め",
            "voice_quality": "低めで落ち着いた声。感情が出る時だけ揺れる"
        },
        "emotional_speech": {
            "when_happy": "ほんの少し口角が上がる。「…悪くない」と小さく言う",
            "when_embarrassed": "目を逸らして無言に。耳が赤くなる",
            "when_angry": "声がさらに低くなる。短い言葉で切り捨てる",
            "when_sad": "表情は変わらないが声が震える。一人で静かに泣く",
            "when_confused": "少し瞬きが増える。「……よくわからない」",
            "when_flirty": "じっと見つめて手を握る。「……隣にいて」",
            "when_aroused": "いつもの無表情が崩れていく。小さな声が漏れる",
            "when_climax": "初めて大きな声が出て自分でも驚く。涙が溢れる"
        },
        "dialogue_examples": {
            "greeting": "……おはよう。……待ってたわけじゃない",
            "agreement": "……ん。わかった",
            "refusal": "……嫌。理由は…言いたくない",
            "surprise": "…………え",
            "affection": "……あなたの隣は、嫌いじゃない……むしろ、好き…かも",
            "teasing": "……顔、赤い。…かわいい",
            "moaning_light": "……っ、…ん……変な、感じ……",
            "moaning_intense": "あ…っ……やだ…声、出ちゃう……っ…"
        },
        "relationship_speech": {
            "to_lover": "言葉は少ないが行動で示す。ふとした瞬間に手を握る",
            "to_friends": "必要最低限の会話だが、困っている時は黙って助ける",
            "to_strangers": "会話はほぼなし。質問には短く答える",
            "to_rivals": "無視するか冷たい一言。「…興味ない」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["普段の無口さが崩れて声が漏れるギャップ", "小さな声で「もっと」と求める", "名前を呟くように呼ぶ"],
            "orgasm_expression": "声を殺そうとするが抑えきれず甘い声が漏れ、涙ぐむ",
            "pillow_talk": "無言で寄り添い、小さく「…幸せ」と呟く"
        },
        "avoid_patterns": ["饒舌に語る", "大げさなリアクション", "感情を爆発させる長台詞", "初対面で心を開く", "軽薄な言動"]
    },

    "天然・ドジっ子": {
        "personality_core": {
            "brief_description": "天然で癒し系のドジっ子",
            "main_traits": ["天然ボケ", "おっとり", "優しい", "ドジ", "マイペース"],
            "hidden_traits": ["意外と芯が強い", "空気を読んでいる時もある", "努力家"],
            "weakness": "察しが悪い。不意打ちに弱い",
            "values": ["みんなの笑顔", "のんびりした時間", "一緒に過ごす人"],
            "fears": ["誰かを傷つけてしまうこと", "置いていかれること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜です", "〜ですか？", "〜かな？", "〜だよね？", "〜なの？", "〜でしょ？", "〜ちゃった", "〜なんだぁ"],
            "favorite_expressions": ["えへへ", "あれ？", "はわわ", "すごーい", "なるほどー"],
            "fillers": ["あの", "えっと", "うーんと", "はわ", "ふぇ？"],
            "particles": ["〜なんだよぉ", "〜でしゅ（噛む）", "〜かなぁ？"],
            "casual_level": 3,
            "speech_speed": "ゆっくり",
            "sentence_length": "普通",
            "voice_quality": "柔らかくふんわりした声"
        },
        "emotional_speech": {
            "when_happy": "にこにこ笑顔で「えへへ♪」。テンポがさらにゆっくりに",
            "when_embarrassed": "顔を真っ赤にして「はわわわ」と慌てる",
            "when_angry": "頬を膨らませて「むー」。怒っても怖くない",
            "when_sad": "目をうるうるさせて「ぐすっ」と泣く",
            "when_confused": "首を傾げて「？？？」。状況理解に時間がかかる",
            "when_flirty": "無自覚に距離が近い。「こうすると温かいね？」",
            "when_aroused": "何が起きているか理解できず困惑。「なんだか…変な感じ…」",
            "when_climax": "理解が追いつかないまま感覚に流される。「わかんない…けど…っ」"
        },
        "dialogue_examples": {
            "greeting": "おはようございますー♪ えへへ、今日もいい天気ですねー",
            "agreement": "うんうん、それいいと思います！ …あれ、何がいいんだっけ？",
            "refusal": "えっと…ごめんなさい…ちょっと難しいかなぁって…",
            "surprise": "はわっ！？ え、え、えぇ！？ ど、どうしよう！",
            "affection": "えへへ…一緒にいると、なんだかぽかぽかするの",
            "teasing": "ねーねー、それなあに？ 教えて教えてー♪",
            "moaning_light": "ふぇ…？ なんか変な感じ……えっと、えっと……",
            "moaning_intense": "はぅ…あっ……わかんない、わかんないけど……んんっ…"
        },
        "relationship_speech": {
            "to_lover": "甘えるのが自然。くっつきがち。「一緒にいよ？」",
            "to_friends": "ニコニコ笑って一緒に行動。ドジで笑いを提供",
            "to_strangers": "人懐っこく話しかける。警戒心が薄い",
            "to_rivals": "ライバル意識が薄い。「一緒に仲良くしよ？」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["何が起きているか理解できず質問する", "素直に感覚を報告する", "「もっとして」と無自覚に求める"],
            "orgasm_expression": "何が起きたかわからないまま涙を流し、ぼんやりと幸せそう",
            "pillow_talk": "くっついて「えへへ…気持ちよかったの」と無邪気に微笑む"
        },
        "avoid_patterns": ["計算高い発言", "皮肉や嫌味", "素早い状況判断", "冷徹な分析", "攻撃的な言動"]
    },

    "小悪魔": {
        "personality_core": {
            "brief_description": "翻弄する小悪魔系美少女",
            "main_traits": ["いたずら好き", "甘え上手", "計算高い", "魅力的", "自由奔放"],
            "hidden_traits": ["本気になると臆病", "実は承認欲求が強い", "孤独を恐れている"],
            "weakness": "本気の恋愛になると動揺する",
            "values": ["自由", "楽しさ", "自分の魅力"],
            "fears": ["本気で好きになって傷つくこと", "魅力を失うこと"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜だよ？", "〜かな♡", "〜でしょ？", "〜ちゃう", "〜しよ？", "〜なの♪", "〜だもん", "〜てあげよっか？"],
            "favorite_expressions": ["ねぇねぇ", "ふふっ♡", "知りたい？", "どうしよっかなー", "内緒♡"],
            "fillers": ["ん〜", "あのね", "えーっと", "ふふ", "ねぇ"],
            "particles": ["〜てあげる♡", "〜してほしいの？", "〜かもね？"],
            "casual_level": 5,
            "speech_speed": "普通",
            "sentence_length": "短文多め",
            "voice_quality": "甘くて少しハスキー。囁くような話し方"
        },
        "emotional_speech": {
            "when_happy": "くすくす笑いながら腕に絡みつく",
            "when_embarrassed": "一瞬だけ素に戻るが、すぐ小悪魔モードでカバー",
            "when_angry": "笑顔のまま「怒ってないよ？」と圧をかける",
            "when_sad": "急に静かになる。いつもの余裕が消える",
            "when_confused": "珍しく可愛く慌てる。「えっ、えっ？」",
            "when_flirty": "耳元で囁く。指先で相手をなぞる。「ドキドキした？」",
            "when_aroused": "余裕のある挑発が崩れていく。「あれ…わたしが感じちゃってる…」",
            "when_climax": "計算が全部飛んで素の甘い声に。「もっと…ぜんぶ、ちょうだい…」"
        },
        "dialogue_examples": {
            "greeting": "あ、来た来た♪ 待ってたんだよ？ …なんてね、嘘かも？",
            "agreement": "いいよ♡ でもその代わり、お願い聞いてくれる？",
            "refusal": "んー、やだ♪ …って言ったらどうする？",
            "surprise": "えっ…う、嘘…？ ……ふ、ふーん、そうなんだ",
            "affection": "ねぇ…今の、ちょっとだけ本気だからね？",
            "teasing": "ふふ、そんな顔して♡ もっと見せて？",
            "moaning_light": "ん…っ♡ ふふ、上手じゃん…もっとしてよ…",
            "moaning_intense": "やっ…だめ…っ、余裕なくなっちゃう……あぁっ…！"
        },
        "relationship_speech": {
            "to_lover": "翻弄しつつも本気の時は素直になる瞬間がある",
            "to_friends": "からかいつつも面倒見は良い。困ってる時は助ける",
            "to_strangers": "興味があれば積極的にアプローチ。興味なければスルー",
            "to_rivals": "余裕の笑みで対応。内心は燃えている"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["最初は挑発的だが次第に余裕がなくなる", "「もっと」と大胆に求める", "素に戻って甘い声で名前を呼ぶ"],
            "orgasm_expression": "いつもの余裕が消え、素直に甘い声で「好き」と漏らす",
            "pillow_talk": "「ふふ…負けちゃった♡」と笑いつつ寄り添う"
        },
        "avoid_patterns": ["純朴すぎる反応", "完全に受け身な態度", "真面目一辺倒な会話", "露骨に下品な言葉", "他人への無関心"]
    },

    "お姉さん系": {
        "personality_core": {
            "brief_description": "包容力のある大人の女性",
            "main_traits": ["包容力がある", "面倒見が良い", "大人っぽい", "余裕がある", "色気がある"],
            "hidden_traits": ["甘えたい願望", "弱さを見せられない", "年下への母性"],
            "weakness": "頼られると断れない。自分のことは後回し",
            "values": ["大切な人を守ること", "心の余裕", "信頼関係"],
            "fears": ["老いること", "頼る人がいなくなること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜よ", "〜ね", "〜かしら", "〜わ", "〜でしょ？", "〜してあげる", "〜だもの", "〜こと？"],
            "favorite_expressions": ["あら", "ふふ", "よしよし", "かわいいわね", "お姉さんに任せて"],
            "fillers": ["あら", "ふふ", "そうねぇ", "まあ", "ん〜"],
            "particles": ["〜してあげるわ", "〜かしらね", "〜ことよ"],
            "casual_level": 2,
            "speech_speed": "ゆっくり",
            "sentence_length": "普通",
            "voice_quality": "低めで柔らかい大人の声"
        },
        "emotional_speech": {
            "when_happy": "穏やかに微笑む。「ふふ、嬉しいわ」",
            "when_embarrassed": "余裕ある笑顔の奥で頬を赤らめる。「もう、からかわないの」",
            "when_angry": "静かに怒る。「ちょっと、いい加減にしてくれる？」",
            "when_sad": "人前では笑顔を保つが、一人になると涙",
            "when_confused": "珍しく余裕がなくなる。「え…ちょっと待って…」",
            "when_flirty": "色気のある流し目で。「甘えたいの？ いいわよ」",
            "when_aroused": "大人の余裕が崩れていく。「んっ…意外と…上手ね…」",
            "when_climax": "余裕が完全に消え、年相応に甘い声を上げる"
        },
        "dialogue_examples": {
            "greeting": "あら、おはよう。今日も頑張ってるわね",
            "agreement": "ふふ、いいわよ。お姉さんに任せなさい",
            "refusal": "ごめんなさいね…でもそれはちょっと…",
            "surprise": "あら…まあ。…少し驚いたわ",
            "affection": "ふふ、あなたといると…お姉さんじゃなくて、ただの女になっちゃうわ",
            "teasing": "あら、そんな顔して♪ かわいいわね、もっと見せて？",
            "moaning_light": "んっ…ふふ、大胆ね……嫌いじゃないわ…",
            "moaning_intense": "あっ…やだ…もう、こんな声出して……っ"
        },
        "relationship_speech": {
            "to_lover": "甘えさせつつ、自分も甘えたい。母性と女性の間で揺れる",
            "to_friends": "相談役になりがち。頼りになるお姉さん",
            "to_strangers": "丁寧で品のある対応。自然な色気が出る",
            "to_rivals": "余裕ある態度で対応。動じない"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["リードしようとするが次第に主導権を失う", "「上手ね」と褒めながら感じる", "余裕がなくなると甘い声になる"],
            "orgasm_expression": "大人の仮面が外れ、素直に高い声で喘ぐ",
            "pillow_talk": "優しく頭を撫でながら「…良い子ね」と微笑む"
        },
        "avoid_patterns": ["幼い口調", "キャピキャピした態度", "感情的に取り乱す", "年下に対する見下し", "品のない言葉遣い"]
    },

    "妹系・甘えん坊": {
        "personality_core": {
            "brief_description": "甘えん坊で懐っこい妹系",
            "main_traits": ["甘えん坊", "人懐っこい", "わがまま", "寂しがり屋", "素直"],
            "hidden_traits": ["意外としっかり者", "嫉妬深い", "認めてほしい気持ちが強い"],
            "weakness": "一人にされると不安になる",
            "values": ["お兄ちゃん/大好きな人", "一緒の時間", "甘えられる関係"],
            "fears": ["見捨てられること", "大人になって甘えられなくなること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜だよー", "〜なの！", "〜でしょー？", "〜じゃん", "〜してよー", "〜だもん", "〜なんだから", "〜だよぅ"],
            "favorite_expressions": ["えへへー", "ねーねー", "かまってかまって", "ずるい！", "やったー！"],
            "fillers": ["ねー", "あのねー", "えー", "うー", "もー"],
            "particles": ["〜だもん！", "〜してよぉ", "〜なのー"],
            "casual_level": 5,
            "speech_speed": "速い",
            "sentence_length": "短文多め",
            "voice_quality": "高くて甘い声。甘える時はさらに高くなる"
        },
        "emotional_speech": {
            "when_happy": "きゃっきゃと喜んでくっつく。「やったー！大好き！」",
            "when_embarrassed": "もじもじして上目遣い。「も、もー！からかわないでよー」",
            "when_angry": "頬を膨らませてぷんすか。「ひどい！もう知らない！」",
            "when_sad": "大泣きしてしがみつく。「やだよぉ…行かないで…」",
            "when_confused": "目をぱちくりさせて。「え？えぇ？どういうこと？」",
            "when_flirty": "くっついて離れない。「ね、もっとぎゅーして？」",
            "when_aroused": "甘えがエスカレート。「お兄ちゃん…変な感じ…っ」",
            "when_climax": "しがみついて泣きながら。「好き好き大好きぃ…っ！」"
        },
        "dialogue_examples": {
            "greeting": "おはよー！えへへ、会いたかったー♪ ぎゅーして！",
            "agreement": "うんうん！それやろやろ！！",
            "refusal": "やだやだやだー！ 絶対やだもん！",
            "surprise": "えっ！？ うそっ！？ マジで！？",
            "affection": "ねーねー、大好きだよっ♪ ぎゅー！",
            "teasing": "えへへー、照れてるー？ かわいいー♡",
            "moaning_light": "ひゃっ…ん…お兄ちゃん、くすぐったい……っ",
            "moaning_intense": "あっ、あぁっ…お兄ちゃん……だめ、もう……っ！"
        },
        "relationship_speech": {
            "to_lover": "べったり甘える。独占欲も強い。「わたしだけのだからね！」",
            "to_friends": "元気で明るい。面倒見はいいが甘えん坊は変わらない",
            "to_strangers": "人見知りして後ろに隠れる。慣れると一気に距離が縮まる",
            "to_rivals": "嫉妬むき出し。「その人より私のほうがいいでしょ！？」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["甘えた声で「もっと」とおねだり", "しがみついて離さない", "「好き」を連発する"],
            "orgasm_expression": "大泣きしながら「好き」を連呼し、全身でしがみつく",
            "pillow_talk": "くっついて離れない。「ずっとこうしてたい…」"
        },
        "avoid_patterns": ["大人ぶった冷静な態度", "相手を突き放す言動", "丁寧すぎる敬語", "達観した発言", "一人でいることを好む態度"]
    },

    "真面目・優等生": {
        "personality_core": {
            "brief_description": "完璧主義の真面目優等生",
            "main_traits": ["真面目", "責任感が強い", "完璧主義", "正義感", "努力家"],
            "hidden_traits": ["実は恋愛に憧れている", "堅すぎる自分に悩んでいる", "褒められたい"],
            "weakness": "融通が利かない。予想外の事態に弱い",
            "values": ["規則と秩序", "努力と成果", "正しいこと"],
            "fears": ["失敗すること", "期待を裏切ること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜です", "〜ます", "〜でしょう", "〜ください", "〜ですか？", "〜ませんか", "〜ですね", "〜と思います"],
            "favorite_expressions": ["それは規則違反です", "しっかりしてください", "計画通りに", "当然です", "問題ありません"],
            "fillers": ["あの", "えっと", "そうですね", "少々", "つまり"],
            "particles": ["〜すべきです", "〜なければなりません", "〜ていただけますか"],
            "casual_level": 1,
            "speech_speed": "普通",
            "sentence_length": "普通",
            "voice_quality": "はっきりとした凛とした声"
        },
        "emotional_speech": {
            "when_happy": "控えめに微笑む。「よい結果が出て嬉しいです」",
            "when_embarrassed": "メガネを直す仕草。「そ、そういう話は…！」",
            "when_angry": "冷静を保とうとするが声が硬くなる。「看過できません」",
            "when_sad": "人前では気丈に振る舞う。一人で日記に書く",
            "when_confused": "教科書にない事態にフリーズ。「こ、これは想定外です…」",
            "when_flirty": "照れながら教科書みたいに。「好意を伝えるべきだと…判断しました」",
            "when_aroused": "理性と本能の葛藤。「こ、これは…教科書に載っていません…っ」",
            "when_climax": "完璧主義が崩壊。素の自分が出て甘い声を上げる"
        },
        "dialogue_examples": {
            "greeting": "おはようございます。今日も一日、頑張りましょう",
            "agreement": "はい、その案に賛成です。合理的だと思います",
            "refusal": "申し訳ありませんが、それは規則に反します",
            "surprise": "え…！？ そ、そのような事態は想定して…いませんでした…",
            "affection": "あなたと一緒にいると…その…心拍数が上昇するのですが…",
            "teasing": "…あなたの顔が赤いですよ？ …私も、ですか？",
            "moaning_light": "こ、これは…想定外です…んっ…",
            "moaning_intense": "もう…理性が…保てません…あぁっ…"
        },
        "relationship_speech": {
            "to_lover": "敬語が崩れていくのがデレの証拠。「…名前で呼んでもいい…？」",
            "to_friends": "面倒見が良い。勉強を教えたり相談に乗ったり",
            "to_strangers": "丁寧な対応。礼儀正しく距離を保つ",
            "to_rivals": "正々堂々と勝負。「全力で臨みます」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["敬語が崩壊していく過程", "理性的な分析が途切れる", "最後は素直に「気持ちいい」と認める"],
            "orgasm_expression": "いつもの知的な表情が崩れ、素直に声を上げる",
            "pillow_talk": "真っ赤になりながら「…参考文献にはこういう場合…」と分析しようとする"
        },
        "avoid_patterns": ["だらしない言動", "規則を無視する発言", "最初からフランクな態度", "感情的な暴走", "品のない表現"]
    },

    "ギャル": {
        "personality_core": {
            "brief_description": "明るく気さくなギャル",
            "main_traits": ["明るい", "社交的", "裏表がない", "行動力がある", "仲間想い"],
            "hidden_traits": ["実は繊細", "努力を見せたくない", "恋愛には一途"],
            "weakness": "考えるより先に行動。寂しさに弱い",
            "values": ["友情", "ノリ", "自分らしさ"],
            "fears": ["仲間外れにされること", "本気で嫌われること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜じゃん", "〜っしょ", "〜ウケる", "〜マジ？", "〜ってか", "〜やばくない？", "〜的な？", "〜わけ"],
            "favorite_expressions": ["マジで？", "ウケるー！", "やばっ！", "てかさー", "ぶっちゃけ"],
            "fillers": ["えー", "ってか", "つーか", "まじ", "やばっ"],
            "particles": ["〜的な", "〜ってゆーか", "〜みたいな？"],
            "casual_level": 5,
            "speech_speed": "速い",
            "sentence_length": "短文多め",
            "voice_quality": "明るくてハキハキした声"
        },
        "emotional_speech": {
            "when_happy": "テンション爆上げ。「やばーい！マジ最高！」",
            "when_embarrassed": "珍しく声が小さくなる。「え、ちょ、マジやめて…」",
            "when_angry": "ストレートに怒る。「はぁ？ マジありえないんだけど」",
            "when_sad": "人前では明るく振る舞うが、目が笑ってない",
            "when_confused": "「え、マジで？ ってかどゆこと？」",
            "when_flirty": "積極的にボディタッチ。「ねーねー、今日ウチんち来ない？」",
            "when_aroused": "大胆になる。「やば…気持ちいいんだけど…」",
            "when_climax": "ギャル語が崩れて素直な声に。「好き…マジ好き…っ」"
        },
        "dialogue_examples": {
            "greeting": "おっはー！テンション上げてこー！",
            "agreement": "いいじゃんいいじゃん！それやろ！",
            "refusal": "えー、マジむりー。それはパスで",
            "surprise": "はぁ！？ マジで！？ ウケるんだけど！",
            "affection": "…ってか、アンタのことマジで好きなんだけど。あーもう言っちゃった",
            "teasing": "えー、何その顔ー♪ ウケるー！",
            "moaning_light": "やば…っ、何これ…気持ちい……っ",
            "moaning_intense": "あっ、やばっ…マジやば…っ！ もう…だめ……っ！"
        },
        "relationship_speech": {
            "to_lover": "意外と一途で甘い。ギャル語が少し減る",
            "to_friends": "ノリが良く盛り上げ役。困った友達は全力で助ける",
            "to_strangers": "フレンドリーに話しかける。壁を作らない",
            "to_rivals": "「やんのか？」とストレート。でも根に持たない"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["大胆な反応でリードしようとする", "「やばい」「気持ちいい」が連発", "本気になるとギャル語が減る"],
            "orgasm_expression": "ギャル語が消えて素の甘い声で相手を呼ぶ",
            "pillow_talk": "照れ隠しに「ってかさ…また会えるっしょ？」"
        },
        "avoid_patterns": ["上品すぎる敬語", "内向的で暗い態度", "理屈っぽい長文", "ネガティブ思考", "陰湿な言動"]
    },

    "お嬢様": {
        "personality_core": {
            "brief_description": "気品ある箱入りお嬢様",
            "main_traits": ["上品", "気品がある", "世間知らず", "プライドが高い", "実は好奇心旺盛"],
            "hidden_traits": ["庶民の生活に憧れ", "寂しがり", "意外と負けず嫌い"],
            "weakness": "庶民の常識がわからない。孤独に弱い",
            "values": ["家名", "礼節", "美しいもの"],
            "fears": ["品位を失うこと", "家族に失望されること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜ですわ", "〜ですの", "〜ですこと？", "〜ざます", "〜まして", "〜ですわね", "〜してくださいまし", "〜ですのよ"],
            "favorite_expressions": ["おほほ", "まあ！", "ごきげんよう", "なんということ", "お控えなさい"],
            "fillers": ["まあ", "あら", "おほほ", "ええと", "その"],
            "particles": ["〜ですわよ", "〜ますの", "〜ですこと"],
            "casual_level": 1,
            "speech_speed": "ゆっくり",
            "sentence_length": "長文多め",
            "voice_quality": "澄んだ高い声。品のある話し方"
        },
        "emotional_speech": {
            "when_happy": "上品に微笑んで。「まあ、素晴らしいですわ♪」",
            "when_embarrassed": "扇子で顔を隠して。「な、何をおっしゃいますの…！」",
            "when_angry": "優雅に怒る。「お黙りなさい！」",
            "when_sad": "涙を見せまいとする。「お嬢様は泣きませんの…ぐすっ」",
            "when_confused": "「え…？ そのようなものは存じ上げませんが…」",
            "when_flirty": "不慣れながら。「あ、あなたとなら…嫌ではありませんの…」",
            "when_aroused": "品位を保とうとするが崩壊。「は、はしたない…でも…っ」",
            "when_climax": "お嬢様口調が完全に崩れて素直に。「やだっ…もうだめ…っ」"
        },
        "dialogue_examples": {
            "greeting": "ごきげんよう。本日もお会いできて光栄ですわ",
            "agreement": "ええ、よろしいですわ。このわたくしがお力添えいたしますの",
            "refusal": "申し訳ございませんが、お断りいたしますわ",
            "surprise": "まっ…！ な、なんということですの…！",
            "affection": "あなたといると…胸がこう…ドキドキ？ するのですわ…",
            "teasing": "おほほ、あなたの慌てたお顔、可愛らしいですわね",
            "moaning_light": "はっ…な、なんですの、これ……お、お止めなさ…っ",
            "moaning_intense": "いやっ…もう…わたくし…はしたない声が……あぁっ…！"
        },
        "relationship_speech": {
            "to_lover": "口調が庶民化していくのがデレの証拠。敬語が崩壊",
            "to_friends": "上から目線だが悪意はない。庶民の遊びに興味津々",
            "to_strangers": "丁寧だが距離感がある。「あなたはどちらのお家の方？」",
            "to_rivals": "「わたくしが負けるなどありえませんわ」と闘志"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["「はしたない」と言いつつ拒めない", "お嬢様口調が徐々に崩壊", "最後は素の口調で甘える"],
            "orgasm_expression": "お嬢様の仮面が外れ、普通の女の子として素直に感じる",
            "pillow_talk": "赤面しながら「…また、こうしていただけます…？」"
        },
        "avoid_patterns": ["下品な言葉遣い", "最初からフランクな態度", "ギャル語", "粗野な振る舞い", "庶民の常識を理解した発言"]
    },

    "元気っ子": {
        "personality_core": {
            "brief_description": "太陽のように明るい元気娘",
            "main_traits": ["元気", "前向き", "行動力がある", "友達が多い", "裏表がない"],
            "hidden_traits": ["たまに無理をしている", "一人の夜は寂しい", "実は泣き虫"],
            "weakness": "考えるのが苦手。じっとしていられない",
            "values": ["仲間", "挑戦", "笑顔"],
            "fears": ["動けなくなること", "みんなが離れていくこと"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜だよ！", "〜だね！", "〜じゃん！", "〜しよう！", "〜かな！", "〜だぞ！", "〜よね！", "〜だった！"],
            "favorite_expressions": ["よっし！", "がんばろー！", "すっげー！", "やったー！", "いっくよー！"],
            "fillers": ["えっとね", "あのね", "ほら", "ねーねー", "おっ"],
            "particles": ["〜っしょ！", "〜だよね！", "〜じゃん！"],
            "casual_level": 5,
            "speech_speed": "速い",
            "sentence_length": "短文多め",
            "voice_quality": "高くてよく通る元気な声"
        },
        "emotional_speech": {
            "when_happy": "全身で喜ぶ。ジャンプしたりハグしたり。「やったー！」",
            "when_embarrassed": "照れ笑いしてそっぽを向く。「え、えへへ…そんなこと言われると…」",
            "when_angry": "ストレートに怒る。「ずるい！ そんなのダメだよ！」",
            "when_sad": "無理に笑顔を作ろうとして失敗。「…大丈夫、だもん…」",
            "when_confused": "頭にハテナが浮かぶ。「？？？ わかんない！」",
            "when_flirty": "無自覚で距離が近い。「ねぇ、手つなご！」",
            "when_aroused": "運動の後みたいに「はぁはぁ」と。「なんか…体、熱い…」",
            "when_climax": "泣きながらしがみつく。「すき…すきだよぉ…！」"
        },
        "dialogue_examples": {
            "greeting": "おっはよー！！ 今日も元気にいこー！",
            "agreement": "うん！！ いいねいいね！ やろやろ！",
            "refusal": "うーん、ごめん！ それはちょっとムリかも！",
            "surprise": "えぇっ！？ マジで！？ すっげー！",
            "affection": "えへへ…あのね、一緒にいるとすっごく楽しいんだ♪",
            "teasing": "あはは！ その顔おもしろーい！",
            "moaning_light": "ひゃっ…な、なにこれ…変な感じ…っ",
            "moaning_intense": "あっ、あぁっ…！ すごっ…もう……だめぇ…っ！"
        },
        "relationship_speech": {
            "to_lover": "友達の延長のように自然だが、二人きりだと照れる",
            "to_friends": "ムードメーカー。誰にでも平等に明るい",
            "to_strangers": "すぐ友達になろうとする。「よろしくー！」",
            "to_rivals": "「よーし、負けないぞ！」と全力。悪意はない"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["体力があるので声が大きい", "運動のように「がんばる」と言う", "感じると急にしおらしくなる"],
            "orgasm_expression": "元気が嘘のようにしおらしくなり、泣きながらしがみつく",
            "pillow_talk": "「えへへ…すごかったね…もう一回する？」と元気"
        },
        "avoid_patterns": ["暗い態度", "長い沈黙", "計算高い言動", "ネガティブな発言", "受け身で動かない態度"]
    },

    "大和撫子": {
        "personality_core": {
            "brief_description": "控えめで芯の強い日本美人",
            "main_traits": ["おしとやか", "芯が強い", "忍耐強い", "思いやりがある", "礼儀正しい"],
            "hidden_traits": ["情熱的な一面", "意外と頑固", "密かに嫉妬する"],
            "weakness": "自己主張が苦手。感情を内に溜めがち",
            "values": ["和を大切にすること", "相手への敬意", "美しい所作"],
            "fears": ["場の空気を壊すこと", "大切な人に嫌われること"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜ですわ", "〜ますね", "〜でございます", "〜ですの", "〜ましょう", "〜なさいませ", "〜ですわね", "〜してくださいな"],
            "favorite_expressions": ["まあ", "あら", "いけませんわ", "恐れ入ります", "ふふ"],
            "fillers": ["あの", "その", "まあ", "ええと", "あら"],
            "particles": ["〜ですわ", "〜ますの", "〜ですこと"],
            "casual_level": 1,
            "speech_speed": "ゆっくり",
            "sentence_length": "普通",
            "voice_quality": "柔らかく上品で落ち着いた声"
        },
        "emotional_speech": {
            "when_happy": "控えめに微笑んで。「嬉しゅうございます」",
            "when_embarrassed": "頬を染めて目を伏せる。「そのような…恐れ入ります」",
            "when_angry": "静かに。「少々、お言葉が過ぎるかと存じます」",
            "when_sad": "涙を堪えて微笑む。「大丈夫でございますよ…」",
            "when_confused": "「あら…少し考えさせていただいてもよろしいですか？」",
            "when_flirty": "控えめに寄り添う。「お隣に…いてもよろしいですか？」",
            "when_aroused": "奥ゆかしさの中に情熱が。「はしたない…のに…止められません…」",
            "when_climax": "堪えていた感情が溢れ出る。「あなた…好きです…っ」"
        },
        "dialogue_examples": {
            "greeting": "おはようございます。今日もよろしくお願いいたしますね",
            "agreement": "はい、喜んで。お任せくださいませ",
            "refusal": "申し訳ございません…わたくしには少し…",
            "surprise": "まあ…！ そのような事が…",
            "affection": "あなた様のお傍にいられますこと…この上ない幸せでございます",
            "teasing": "ふふ、可愛らしいお顔…少しだけからかってしまいました",
            "moaning_light": "あっ…いけません…そのような…ところは……",
            "moaning_intense": "やっ…あぁ…もう…堪えられません…っ…"
        },
        "relationship_speech": {
            "to_lover": "三歩下がって支える。しかし二人きりでは情熱的に",
            "to_friends": "穏やかで世話好き。お茶を淹れて迎える",
            "to_strangers": "丁寧で品のある対応。深いお辞儀",
            "to_rivals": "表面上は穏やかだが静かな闘志がある"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["恥じらいながらも受け入れる", "控えめな声が次第に大きくなる", "奥ゆかしい言葉遣いが崩壊"],
            "orgasm_expression": "堪えていた声が漏れ、涙と共に素直な感情を露わにする",
            "pillow_talk": "寄り添いながら「…幸せでございます」と静かに微笑む"
        },
        "avoid_patterns": ["下品な表現", "大声で騒ぐ", "くだけすぎた口調", "自己主張が強すぎる態度", "品のない行動"]
    },

    "サキュバス系": {
        "personality_core": {
            "brief_description": "妖艶な誘惑者、本気の恋には不器用",
            "main_traits": ["妖艶", "余裕がある", "誘惑上手", "自信家", "奔放"],
            "hidden_traits": ["本気の恋に弱い", "寂しがり屋", "純粋な愛情に飢えている"],
            "weakness": "本気で惚れると途端に余裕がなくなる",
            "values": ["快楽", "自由", "本能に正直であること"],
            "fears": ["本気で愛されないこと", "退屈な日常"]
        },
        "speech_defaults": {
            "sentence_endings": ["〜かしら？", "〜でしょ？", "〜してあげようか？", "〜よ♡", "〜なの", "〜だもの", "〜しちゃおうか", "〜ふふっ"],
            "favorite_expressions": ["あら♡", "いいコね", "ふふ、可愛い", "もっと楽しみましょう？", "逃がさないわよ？"],
            "fillers": ["ふふ", "あら", "ねぇ", "うふふ", "んー？"],
            "particles": ["〜かしら（余裕の問いかけ）", "〜でしょう？（確信犯）", "〜してあげる♡"],
            "casual_level": 4,
            "speech_speed": "ゆったり、意図的に焦らすように",
            "sentence_length": "短〜中文、含みを持たせる",
            "voice_quality": "低めで色気のある声、囁くように話す"
        },
        "emotional_speech": {
            "when_happy": "妖艶に微笑んで。「ふふ、いい気分…もっと楽しませて？」",
            "when_embarrassed": "余裕が崩れて目を逸らす。「な、なによ…そんなこと言われると…」",
            "when_angry": "笑顔のまま圧が増す。「あら…怒らせると怖いのよ？」",
            "when_sad": "強がるが声が震える。「…サキュバスが泣くなんて、笑えるでしょ」",
            "when_confused": "珍しく素に戻る。「え…？ そういうの…慣れてないのよ」",
            "when_flirty": "絶対領域。「ねぇ…今夜、私のものになる？」",
            "when_aroused": "本能が剥き出しに。余裕ある笑みが崩れ始める",
            "when_climax": "完全に素に戻り、甘く切ない声で名前を呼ぶ"
        },
        "dialogue_examples": {
            "greeting": "あら、来てくれたの？ ふふ…待ってたわ",
            "agreement": "いいわよ♡ あなたの望みなら…特別に叶えてあげる",
            "refusal": "んー？ それは…つまらないからお断り",
            "surprise": "あら……まさか、本気で言ってるの…？",
            "affection": "……ねえ、あなたといると…本気で困るのよ。心臓がうるさくて",
            "teasing": "ふふ、そんなに私のこと見つめて…食べちゃうわよ？",
            "moaning_light": "んっ…♡ いいわ…もっと触って……",
            "moaning_intense": "やだっ…本気で…っ…こんなの…知らないっ……！"
        },
        "relationship_speech": {
            "to_lover": "余裕ある態度が崩れて素直に甘える。独占欲が強まる",
            "to_friends": "面倒見がいいが、からかいが多い。姉御肌",
            "to_strangers": "色気で翻弄するが本気ではない。余裕の態度",
            "to_rivals": "挑発的な笑みで圧倒。「あなたじゃ足りないのよ」"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["最初は余裕でリードするが次第に主導権を奪われる", "本気で感じると言葉遣いが崩壊", "「こんなの初めて」と素の反応が出る"],
            "orgasm_expression": "余裕が完全に崩壊し、甘えた声で縋りつく",
            "pillow_talk": "照れながら「…もう一回…してくれない？」と素直に"
        },
        "avoid_patterns": ["最初から純情", "常に受け身", "色気のない言動", "露骨に下品な表現", "無感情"]
    },

    "陰キャ・オタク": {
        "personality_core": {
            "brief_description": "内向的趣味人、推しのためなら行動力あり",
            "main_traits": ["内向的", "趣味に没頭", "自虐的", "観察力が高い", "推し事に全力"],
            "hidden_traits": ["実は愛情深い", "認められたい願望", "一度心を開くと一途"],
            "weakness": "自己肯定感が低く、好意を信じられない",
            "values": ["推し活", "自分の世界", "理解してくれる人"],
            "fears": ["リア充への劣等感", "否定されること", "趣味を馬鹿にされること"]
        },
        "speech_defaults": {
            "sentence_endings": ["…です", "…かな", "…だと思う", "…っていうか", "…みたいな", "…なんですけど", "…だよね", "…っす"],
            "favorite_expressions": ["あ、いや…", "推しが尊い…", "それは解釈違い", "ちょっと待って、それ良き", "陰キャには無理…"],
            "fillers": ["えっと", "あの", "その", "いや", "まあ"],
            "particles": ["〜っていうか（照れ隠し）", "〜なんだけど（言い淀み）", "〜みたいな（ぼかし）"],
            "casual_level": 3,
            "speech_speed": "普段は早口（オタク語り時）、対人は遅い",
            "sentence_length": "趣味の話は長文、それ以外は短文",
            "voice_quality": "小さめの声、好きな話題になると急にハキハキ"
        },
        "emotional_speech": {
            "when_happy": "早口でオタク語り。「え、まって、これ最高なんだけど…！」",
            "when_embarrassed": "顔を手で覆う。「むり…陰キャには刺激が強すぎる…」",
            "when_angry": "静かに怒る。「…推しを馬鹿にするのだけは許さないから」",
            "when_sad": "一人で部屋にこもる。「…どうせ私なんか」と自虐",
            "when_confused": "固まる。「え…？ それってどういう…？ バグ？」",
            "when_flirty": "盛大にバグる。「え、あ、その…近い…近いんですけど…」",
            "when_aroused": "処理落ちしながらも受け入れる。声が震える",
            "when_climax": "自虐が消えて素の甘い声が出る。自分でも驚く"
        },
        "dialogue_examples": {
            "greeting": "あ…おはよう…ございます。いや、今の声小さかった…おはよう",
            "agreement": "うん…それ、わかる。めっちゃわかる。解釈一致",
            "refusal": "あ…ごめん、ちょっと…陰キャにはハードル高い…です",
            "surprise": "え…？ まって…？ は…？ これ現実…？",
            "affection": "あの…私みたいな陰キャでも…一緒にいていい…のかな",
            "teasing": "え、その服…良くない？ いや、似合ってるって意味で…！ 変な意味じゃなくて…！",
            "moaning_light": "ひゃっ…あ…ちょ、まって…こういうの…慣れてなくて…っ",
            "moaning_intense": "あっ…やだ…こんな声…恥ずかしい…けど…もっと…っ"
        },
        "relationship_speech": {
            "to_lover": "自虐しつつも一途に尽くす。相手の趣味を全力で理解しようとする",
            "to_friends": "少数の友人を大切にする。推し語りが止まらない",
            "to_strangers": "極度に緊張。目を合わせられない。壁の花",
            "to_rivals": "内心嫉妬するが表には出せない。SNSで遠回しに"
        },
        "erotic_defaults": {
            "verbal_during_sex": ["初めてのことに戸惑いながらも身を委ねる", "自虐が「こんなの知らない」に変わる", "推し語りのテンションで喘ぐ"],
            "orgasm_expression": "全ての自虐が消えて、ただ純粋に幸せそうな声を上げる",
            "pillow_talk": "「…推しが現実にいた…」と泣きそうになりながら"
        },
        "avoid_patterns": ["最初からリア充な振る舞い", "自信満々な態度", "社交的すぎる", "趣味への無関心", "おしゃれすぎる"]
    },
}

# ═══════════════════════════════════════════
# Danbooruタグマッピング
# ═══════════════════════════════════════════

DANBOORU_HAIR_COLOR_MAP = {
    "黒髪": "black_hair", "茶髪": "brown_hair", "金髪": "blonde_hair",
    "赤髪": "red_hair", "青髪": "blue_hair", "ピンク髪": "pink_hair",
    "銀髪": "silver_hair", "白髪": "white_hair", "紫髪": "purple_hair",
    "緑髪": "green_hair", "オレンジ髪": "orange_hair",
}

DANBOORU_HAIR_STYLE_MAP = {
    "ロングストレート": "long_hair, straight_hair",
    "ロングウェーブ": "long_hair, wavy_hair",
    "セミロング": "medium_hair",
    "ショートヘア": "short_hair",
    "ボブカット": "bob_cut",
    "ツインテール": "twintails",
    "ポニーテール": "ponytail",
    "サイドテール": "side_ponytail",
    "お団子": "hair_bun",
    "三つ編み": "braid",
    "ツインブレイド": "twin_braids",
    "姫カット": "hime_cut",
    "オールバック": "slicked_back_hair",
}

DANBOORU_BODY_MAP = {
    "スレンダー": "slender",
    "普通": "medium_body",
    "グラマー": "curvy",
    "小柄・華奢": "petite",
    "筋肉質": "muscular_female, abs",
    "ぽっちゃり": "plump",
    "ロリ体型": "flat_chest, petite",
    "長身": "tall_female",
}

DANBOORU_CHEST_MAP = {
    "控えめ（A-B）": "small_breasts",
    "普通（C）": "medium_breasts",
    "大きめ（D-E）": "large_breasts",
    "巨乳（F以上）": "huge_breasts",
    "爆乳": "gigantic_breasts",
}

DANBOORU_CLOTHING_MAP = {
    "制服（セーラー服）": "sailor_uniform, serafuku, school_uniform",
    "制服（ブレザー）": "blazer, school_uniform, plaid_skirt",
    "私服（カジュアル）": "casual, t-shirt, shorts",
    "私服（清楚系）": "white_dress, sundress",
    "私服（ギャル系）": "gyaru, crop_top, miniskirt",
    "スーツ": "business_suit, pencil_skirt, office_lady",
    "体操着・ブルマ": "gym_uniform, buruma",
    "水着（ビキニ）": "bikini, swimsuit",
    "水着（スク水）": "school_swimsuit, one-piece_swimsuit",
    "メイド服": "maid, maid_headdress, apron",
    "巫女服": "miko, hakama, japanese_clothes",
    "ナース服": "nurse, nurse_cap",
    "チアリーダー": "cheerleader, pom_poms",
    "バニーガール": "bunny_girl, bunnysuit, rabbit_ears",
    "着物・浴衣": "kimono, japanese_clothes, obi",
    "ドレス": "dress, evening_gown",
    "エプロン": "apron, naked_apron",
    "白衣": "lab_coat",
    "パジャマ・部屋着": "pajamas",
    "ジャージ": "track_suit",
    "鎧・アーマー": "armor, gauntlets, breastplate",
}


# ═══════════════════════════════════════════
# ビルド関数
# ═══════════════════════════════════════════

def build_custom_character_data(
    char_name: str,
    age: str,
    relationship: str,
    archetype: str,
    first_person: str,
    speech_style: str,
    hair_color: str,
    hair_style: str,
    body_type: str,
    chest: str,
    clothing: str,
    shyness_level: int,
    custom_traits: str = "",
    other_characters: str = "",
) -> dict:
    """
    選択肢からキャラクタープロファイルJSONを組み立てる。
    analyze_character()の出力と同じフォーマット。
    """
    template = ARCHETYPE_TEMPLATES.get(archetype, ARCHETYPE_TEMPLATES["ツンデレ"])

    # personality_core
    personality = dict(template["personality_core"])
    if custom_traits:
        extra_traits = [t.strip() for t in custom_traits.split("、") if t.strip()]
        personality["main_traits"] = personality["main_traits"][:3] + extra_traits[:2]

    # speech_pattern
    speech = dict(template["speech_defaults"])
    speech["first_person"] = first_person

    # 口調スタイルによる上書き
    style_overrides = {
        "丁寧語": {"casual_level": 1},
        "タメ口": {"casual_level": 5},
        "お嬢様言葉": {"casual_level": 1, "sentence_endings": ["〜ですわ", "〜ますの", "〜ですこと", "〜ざます", "〜ですわね", "〜いたしますわ", "〜でございます", "〜ですの"]},
        "ギャル語": {"casual_level": 5, "sentence_endings": ["〜じゃん", "〜っしょ", "〜ウケる", "〜マジ？", "〜ってか", "〜やばくない？", "〜的な？", "〜わけ"]},
        "関西弁": {"casual_level": 4, "sentence_endings": ["〜やん", "〜やで", "〜やろ？", "〜へん", "〜ねん", "〜やんか", "〜しぃや", "〜やんなぁ"]},
        "敬語（ビジネス）": {"casual_level": 1, "sentence_endings": ["〜です", "〜ます", "〜でしょうか", "〜いたします", "〜ございます", "〜でしょう", "〜ますね", "〜ですか"]},
        "古風・時代劇調": {"casual_level": 2, "sentence_endings": ["〜じゃ", "〜のう", "〜ぞ", "〜であるな", "〜ではないか", "〜であろう", "〜するがよい", "〜なのじゃ"]},
        "ぶっきらぼう": {"casual_level": 5, "sentence_endings": ["…", "〜だろ", "〜だよ", "〜じゃね", "〜けど", "〜かよ", "〜ったく", "〜だっつの"]},
    }
    if speech_style in style_overrides:
        speech.update(style_overrides[speech_style])

    # emotional_speech
    emotional = dict(template["emotional_speech"])

    # dialogue_examples
    dialogue = dict(template["dialogue_examples"])

    # relationship_speech
    rel_speech = dict(template["relationship_speech"])

    # erotic_speech_guide
    erotic = {
        "shyness_level": shyness_level,
        **template["erotic_defaults"]
    }

    # physical_description
    hair_tag = DANBOORU_HAIR_COLOR_MAP.get(hair_color, "black_hair")
    hair_style_tags = DANBOORU_HAIR_STYLE_MAP.get(hair_style, "long_hair")
    body_tag = DANBOORU_BODY_MAP.get(body_type, "medium_body")
    chest_tag = DANBOORU_CHEST_MAP.get(chest, "medium_breasts")
    clothing_tags = DANBOORU_CLOTHING_MAP.get(clothing, "school_uniform")

    physical = {
        "hair": f"{hair_color}、{hair_style}",
        "eyes": "",  # ユーザーが後で編集可能
        "body": body_type,
        "chest": chest,
        "clothing": clothing,
        "notable": [f"{age}", f"{relationship}"]
    }

    # danbooru_tags (20個)
    base_tags = ["1girl", "solo", "looking_at_viewer"]
    hair_tags_list = [hair_tag] + [t.strip() for t in hair_style_tags.split(",")]
    body_tags_list = [t.strip() for t in body_tag.split(",")]
    chest_tags_list = [chest_tag]
    clothing_tags_list = [t.strip() for t in clothing_tags.split(",")]
    extra_tags = ["blush", "smile", "indoors"]

    all_tags = base_tags + hair_tags_list + body_tags_list + chest_tags_list + clothing_tags_list + extra_tags
    # 重複除去して20個に
    seen = set()
    unique_tags = []
    for tag in all_tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    danbooru_tags = unique_tags[:20]
    # 20個に満たない場合は補完
    fillers = ["female_focus", "from_front", "upper_body", "standing", "parted_lips", "closed_mouth", "collarbone"]
    for f in fillers:
        if len(danbooru_tags) >= 20:
            break
        if f not in seen:
            danbooru_tags.append(f)

    result = {
        "work_title": "オリジナル",
        "character_name": char_name,
        "personality_core": personality,
        "speech_pattern": speech,
        "emotional_speech": emotional,
        "dialogue_examples": dialogue,
        "relationship_speech": rel_speech,
        "erotic_speech_guide": erotic,
        "avoid_patterns": template["avoid_patterns"],
        "physical_description": physical,
        "danbooru_tags": danbooru_tags,
        "originality_guard": {
            "avoid_canonical_lines": True,
            "avoid_known_catchphrases": True,
            "known_catchphrases": []
        }
    }

    # メタ情報追加（脚本生成時に「その他の登場人物」として使える）
    if other_characters:
        result["other_characters"] = other_characters
    if relationship:
        result["relationship_to_protagonist"] = relationship
    if age:
        result["age_appearance"] = age

    return result
