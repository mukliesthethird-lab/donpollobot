import discord
from discord import app_commands
from discord.ext import commands
import mysql.connector # Added
import random
import aiohttp
from datetime import datetime, timedelta
from utils.database import get_db_connection

# DB_PATH = 'database.db' # Not used anymore

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.conn = sqlite3.connect(DB_PATH) # Removed SQLite
        self._init_db()
        
        # Cooldown Mappings for Manual Check
        # Normal: 15s, Buff (Rokok Surya): 5s
        # Cooldown Mappings for Manual Check
        # Normal: 15s, Buff (Rokok Surya): 5s
        self.catch_cooldowns = {}
        
        # Fish Data
        # Fish Data Configuration
        # Format: {"name": "Name", "base_price": Price, "min_weight": MinKG, "max_weight": MaxKG, "spawn_weight": Chance}
        self.fish_data = {
        "Common": [
            {"name": "Ikan Mas", "base_price": 10, "min_weight": 0.5, "max_weight": 2.0, "spawn_weight": 50, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445356966728831027/Ikan_Mas.png?ex=69300d12&is=692ebb92&hm=22b706430aa2560777f7980dddb68f945fc6eb197435580f152aae1a42137213&=&format=webp&quality=lossless"},
            {"name": "Lele", "base_price": 12, "min_weight": 0.8, "max_weight": 3.0, "spawn_weight": 45, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445355853338120283/Lele.png?ex=69300c08&is=692eba88&hm=62faa6ddc54bd7bf131d9dc509ea60fb9687bf57770de85a82d1359d7e85cc08&=&format=webp&quality=lossless"},
            {"name": "Nila", "base_price": 15, "min_weight": 0.5, "max_weight": 2.5, "spawn_weight": 40, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445357306832355450/Nila.png?ex=69300d63&is=692ebbe3&hm=7f0e7f13f44bf490222d74824b8098340653b0a42c286b54c213bb2ffb4cc865&=&format=webp&quality=lossless"},
            {"name": "Sepat", "base_price": 8, "min_weight": 0.1, "max_weight": 0.5, "spawn_weight": 60, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445357801856565258/Ikan_Sepat.png?ex=69300dd9&is=692ebc59&hm=2cc87d694fd3d42a919d38dcce951676dc84b0556478fa67a15eb8a01e09eddb&=&format=webp&quality=lossless"},
            {"name": "Mujair", "base_price": 10, "min_weight": 0.4, "max_weight": 1.5, "spawn_weight": 50, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445359331825422457/Ikan_Mujair.png?ex=69300f46&is=692ebdc6&hm=bab544aa9a4d4a71e974cee008d7f184332f4da2094cc84c4fecebd47d72c948&=&format=webp&quality=lossless"}
        ],

        "Uncommon": [
            {"name": "Gurame", "base_price": 25, "min_weight": 1.0, "max_weight": 5.0, "spawn_weight": 30, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445359847431209140/Gurame.png?ex=69300fc1&is=692ebe41&hm=32682550cf3ff7d43219623586be6fdbd0b072da58a34b02b2dca3031c266c2c&=&format=webp&quality=lossless"},
            {"name": "Patin", "base_price": 30, "min_weight": 2.0, "max_weight": 8.0, "spawn_weight": 25, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445361905760997507/Ikan_Patin.png?ex=693011ab&is=692ec02b&hm=d4d71f19b972dc05fb3ee3904994d9bf189f9e15f0e762afdc0adeed403f65ff&=&format=webp&quality=lossless"},
            {"name": "Bawal Hitam", "base_price": 28, "min_weight": 1.5, "max_weight": 6.0, "spawn_weight": 25, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445362880806391849/Ikan_Bawal_Hitam.png?ex=69301294&is=692ec114&hm=23650174a673fee177a51749c44744c702edd03d714f535f79bb3093ac205bfe&=&format=webp&quality=lossless"},
            {"name": "Bandeng", "base_price": 35, "min_weight": 1.0, "max_weight": 4.0, "spawn_weight": 20, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445363601589141605/Bandeng.png?ex=69301340&is=692ec1c0&hm=af21518287673d2060a7f19076f4f9094e8e64140ed78fc3dd57b492a225b923&=&format=webp&quality=lossless"},
            {"name": "Toman", "base_price": 32, "min_weight": 2.0, "max_weight": 10.0, "spawn_weight": 22, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445364602430034032/Toman.png?ex=6930142e&is=692ec2ae&hm=bf74fa7375235e19bdaf841974d78faaea490cfa4e5c4c74de331aefd9599962&=&format=webp&quality=lossless"},
            {"name": "Belida", "base_price": 40, "min_weight": 1.0, "max_weight": 5.0, "spawn_weight": 18, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445364834567852053/BelidA.png?ex=69301466&is=692ec2e6&hm=a2e530cbcce98521fdb6c401e2d57f408baa21872a53095eecc069bffeb91cd8&=&format=webp&quality=lossless"},
            {"name": "Kelah", "base_price": 50, "min_weight": 1.5, "max_weight": 8.0, "spawn_weight": 15, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445365376639832115/Kelah.png?ex=693014e7&is=692ec367&hm=43dc67e298be6e487a8732859255d75541b84b13b2ec3ed3d90d38faba35ee88&=&format=webp&quality=lossless"},
            {"name": "Selar", "base_price": 20, "min_weight": 0.5, "max_weight": 2.0, "spawn_weight": 30, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445365862688362546/Ikan_Selar.png?ex=6930155b&is=692ec3db&hm=941ab673f55447cb09d929fd5e75da3f94d9bebf999cfef1b83985bc21e1def8&=&format=webp&quality=lossless"},
            {"name": "Kembung", "base_price": 22, "min_weight": 0.4, "max_weight": 2.0, "spawn_weight": 28, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445366249155465266/Ikan_Kembung.png?ex=693015b7&is=692ec437&hm=2068d9c7b4ae82d23bcf1bdd6b66d999408b6d2d2c6273e0ad0dd4888151d022&=&format=webp&quality=lossless"},
            {"name": "Layur", "base_price": 38, "min_weight": 1.0, "max_weight": 3.0, "spawn_weight": 20, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445366824911900754/Ikan_Layur.png?ex=69301640&is=692ec4c0&hm=37fa120132f8ed89579bb9c9f1410d519793adb75bd2eb5646051dd57bb64632&=&format=webp&quality=lossless"},
            {"name": "Tongkol", "base_price": 33, "min_weight": 1.0, "max_weight": 4.0, "spawn_weight": 22, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445367428535292016/Tongkol.png?ex=693016d0&is=692ec550&hm=3e2e550b26fba263be2cb23476b90f7552a59863ff28b486af0c1b0da71d92f1&=&format=webp&quality=lossless&width=550&height=300"},
            {"name": "Tambakan", "base_price": 26, "min_weight": 0.3, "max_weight": 1.5, "spawn_weight": 28, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445367743523061853/Tambakan.png?ex=6930171b&is=692ec59b&hm=768c527d8dde91902acc507fd76b1142ad8ea5e7b1639fdfc2411bda22c82df4&=&format=webp&quality=lossless"},
            {"name": "Betutu", "base_price": 45, "min_weight": 0.5, "max_weight": 2.0, "spawn_weight": 16, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445367990882140220/Betutu.png?ex=69301756&is=692ec5d6&hm=45985d5df41d65ce86245190e2f9abcfee9023c078e8e2a05c475cbce686a56e&=&format=webp&quality=lossless"},
            {"name": "Gabus", "base_price": 34, "min_weight": 1.0, "max_weight": 4.0, "spawn_weight": 24, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445368476372832256/Gabus.png?ex=693017ca&is=692ec64a&hm=90e7b45bd12129a8d947c0567f3557d301e1d7d81de14bea11df44e9d6466824&=&format=webp&quality=lossless"},
            {"name": "Bawal Putih", "base_price": 30, "min_weight": 1.0, "max_weight": 4.0, "spawn_weight": 22, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445369132232216686/Bawal_Putih.png?ex=69301866&is=692ec6e6&hm=044449f0c6b98dd5f287358defa3b6b3e14d3dddf425d598ed77f67bcdbe1b5f&=&format=webp&quality=lossless"}
        ],

        "Rare": [
            {"name": "Kakap Merah", "base_price": 80, "min_weight": 3.0, "max_weight": 12.0, "spawn_weight": 15, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445369385224114217/Kakap_Merah.png?ex=693018a3&is=692ec723&hm=bc1a8f285d9ce95c7149444481333b834a3c78463a908b567bb888fbc36013d0&=&format=webp&quality=lossless"},
            {"name": "Kerapu", "base_price": 90, "min_weight": 4.0, "max_weight": 15.0, "spawn_weight": 12, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445369553390669926/Kerapu.png?ex=693018cb&is=692ec74b&hm=22115876b524fe8845f8ae8dd48c54eb66e489801a37d654eaa17cd1cf0fc1eb&=&format=webp&quality=lossless"},
            {"name": "Salmon", "base_price": 120, "min_weight": 5.0, "max_weight": 25.0, "spawn_weight": 10, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445370016064082081/Salmon.png?ex=69301939&is=692ec7b9&hm=bc710599348056308c5bdde7eab3145ea9865f97469b653051ebbd1bd240219a&=&format=webp&quality=lossless"},
            {"name": "Gindara", "base_price": 140, "min_weight": 2.0, "max_weight": 7.0, "spawn_weight": 8, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445370172985835621/Gindara.png?ex=6930195e&is=692ec7de&hm=ca21edbc3d2581cf05006b20e9ed5a633366d11edb9809aa3a4ae63321d19eb7&=&format=webp&quality=lossless"},
            {"name": "Opah", "base_price": 150, "min_weight": 10.0, "max_weight": 90.0, "spawn_weight": 7, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445370573378027553/Opah.png?ex=693019be&is=692ec83e&hm=19d47defb99514e18b60b64232d6f1ce32a7b303a71db1cee065eafbb8edf343&=&format=webp&quality=lossless"},
            {"name": "Arwana Silver", "base_price": 130, "min_weight": 1.0, "max_weight": 6.0, "spawn_weight": 9, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445370841612288091/Arwana_Silver.png?ex=693019fe&is=692ec87e&hm=a816c2947049e3d689605de133aea086fb7b0afaef4bd6db6c896f80b777e8a3&=&format=webp&quality=lossless"},
            {"name": "Tenggiri", "base_price": 85, "min_weight": 3.0, "max_weight": 10.0, "spawn_weight": 14, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445371037150740490/Tenggiri.png?ex=69301a2c&is=692ec8ac&hm=8bbfbdcb3cf47691702d797bbe6bdd5acf3d46d6ad8af86b3082409c4689ab57&=&format=webp&quality=lossless"},
            {"name": "Baronang", "base_price": 70, "min_weight": 1.0, "max_weight": 4.0, "spawn_weight": 15, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445371365585850451/Baronang.png?ex=69301a7b&is=692ec8fb&hm=f005e10a7b7a21ee2e100f8e501ab8fd6e238aee329ee1c996c915a8850592ac&=&format=webp&quality=lossless"},
            {"name": "Kurisi", "base_price": 65, "min_weight": 0.5, "max_weight": 2.0, "spawn_weight": 18, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445371533949272084/Kurisi.png?ex=69301aa3&is=692ec923&hm=6fa89bba428756a829a8c2a9baf65fb963a2aa619b00415d13837fff81dac20e&=&format=webp&quality=lossless"},
            {"name": "Queenfish", "base_price": 90, "min_weight": 2.0, "max_weight": 10.0, "spawn_weight": 11, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445371791873933312/Queenfish.png?ex=69301ae0&is=692ec960&hm=8b873869eda941e605108698d1f5745785668ee1b0b19fbbd7b36a69f4c3e218&=&format=webp&quality=lossless"},
            {"name": "Cakalang", "base_price": 100, "min_weight": 2.0, "max_weight": 6.0, "spawn_weight": 10, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445372001433944225/Cakalang.png?ex=69301b12&is=692ec992&hm=3bf306e4bb42ed808e28aae13fb23261dc886eef1fd0665428620c06d43c9653&=&format=webp&quality=lossless"},
            {"name": "White Seabass", "base_price": 115, "min_weight": 5.0, "max_weight": 20.0, "spawn_weight": 8, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445372208062140467/White_Seabass.png?ex=69301b44&is=692ec9c4&hm=7acb1f31d087da05129e5df82a970e5170148721dab42e26b644e3fe5fa80c09&=&format=webp&quality=lossless"},
            {"name": "Golden Mahseer", "base_price": 150, "min_weight": 2.0, "max_weight": 10.0, "spawn_weight": 6, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445372626435571793/Golden_Mahseer.png?ex=69301ba7&is=692eca27&hm=094c21c626d2e0473b9d481824d917ae78b8dd6fa4bdc03b9a62beddb23962e3&=&format=webp&quality=lossless"},
            {"name": "Lampuga", "base_price": 130, "min_weight": 3.0, "max_weight": 15.0, "spawn_weight": 7, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445373104447553547/Lampuga.png?ex=69301c19&is=692eca99&hm=46fd6d96e0ecf0c3abc78620234aed4dd45dcacef34691e34c8a245c1d993bb0&=&format=webp&quality=lossless"},
            {"name": "Sapu Laut", "base_price": 75, "min_weight": 1.0, "max_weight": 5.0, "spawn_weight": 16, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445373262254051471/sapu_laut.png?ex=69301c3f&is=692ecabf&hm=0aeb987404b602e27b9e359e42ecca247349686ba9333922209064edc694be07&=&format=webp&quality=lossless"},
            {"name": "Nila Merah", "base_price": 100, "min_weight": 0.5, "max_weight": 3.0, "spawn_weight": 12, "image_url": "https://cdn.discordapp.com/attachments/1080697175291469936/1445373494614298814/Nila_merah.png?ex=69301c76&is=692ecaf6&hm=273680a6858a0e77e8912ad78fbbcc296da281ec95b4a21000e480034f891532&"},
            {"name": "Ikan Kurau", "base_price": 110, "min_weight": 3.0, "max_weight": 15.0, "spawn_weight": 8, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445374133700657192/Kurau.png?ex=69301d0f&is=692ecb8f&hm=fc296a847c10f61a0d2c65137c0153a99d65fc53945185a20613442ebfcf6224&=&format=webp&quality=lossless"},
            {"name": "Ikan Gulama", "base_price": 95, "min_weight": 1.0, "max_weight": 3.0, "spawn_weight": 14, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445374491114078438/gulama.png?ex=69301d64&is=692ecbe4&hm=bc5fb4141b47a210e8e1d42dd02ddb8c218cdc131e60420318a54997a7479c2b&=&format=webp&quality=lossless"},
            {"name": "Ikan Kakap Putih", "base_price": 120, "min_weight": 2.0, "max_weight": 8.0, "spawn_weight": 10, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445374681862373407/Ikan_Kakap_Putih.png?ex=69301d91&is=692ecc11&hm=1b7b4045e4d7cfe48c7f76e8b6f6e7dd8ac04484d8c8c66db2234d06b55c6f08&=&format=webp&quality=lossless"}
        ],

        "Epic": [
            {"name": "Arowana Merah", "base_price": 2500, "min_weight": 2.0, "max_weight": 7.0, "spawn_weight": 5, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445374909726457906/Arwana_Merah.png?ex=69301dc8&is=692ecc48&hm=afb3f20caa419385e2af106eea96c904689e9dd6323e05226d2e287a3ddaebe3&=&format=webp&quality=lossless"},
            {"name": "Koi Jumbo", "base_price": 1000, "min_weight": 1.0, "max_weight": 5.0, "spawn_weight": 8, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445375111405244436/koi_jumbo.png?ex=69301df8&is=692ecc78&hm=87645f1d902c920eb6f9729bcef55e75bcb71dae12c79b572964a40bcf6dbf24&=&format=webp&quality=lossless"},
            {"name": "Giant Trevally", "base_price": 800, "min_weight": 5.0, "max_weight": 25.0, "spawn_weight": 4, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445375397624676372/Giant_Trevally.png?ex=69301e3c&is=692eccbc&hm=70402956cd4b1cf531b0f9b01e38f167de78ef505a6dcec7b87d9c345a97dafc&=&format=webp&quality=lossless"},
            {"name": "Sturgeon", "base_price": 2500, "min_weight": 10.0, "max_weight": 50.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445375608044650608/Sturgeon.png?ex=69301e6e&is=692eccee&hm=01c5765451e51dd22b78dba2424b96aed000a201fd72d020ca14e3d61c699d01&=&format=webp&quality=lossless"},
            {"name": "Goliath Tigerfish", "base_price": 3500, "min_weight": 5.0, "max_weight": 30.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445375912861241456/Goliath_Tigerfish.png?ex=69301eb7&is=692ecd37&hm=6c6532c849279b7839877f5a2d43eaa404e22b5ff0693710bbaf77cb0ec9bb17&=&format=webp&quality=lossless"},
            {"name": "Lobster", "base_price": 1500, "min_weight": 0.5, "max_weight": 3.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445376133771165746/Lobster.png?ex=69301eec&is=692ecd6c&hm=99f204d4fd10bc37514dca87c03a989107367476ea9aa49562bcdd02df457d80&=&format=webp&quality=lossless"},
            {"name": "Nile Perch", "base_price": 2000, "min_weight": 10.0, "max_weight": 60.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445376455285669978/Nile_Perch.png?ex=69301f38&is=692ecdb8&hm=315d7e252cf9d6b2233f7b17f878fb7d1eeb92616ce8356de1d3f3a2231d209c&=&format=webp&quality=lossless"},
            {"name": "Wahoo", "base_price": 1500, "min_weight": 3.0, "max_weight": 20.0, "spawn_weight": 4, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445376863324209315/ikan_wahoo.png?ex=69301f9a&is=692ece1a&hm=b1f1da379c50e259bd1cfd84920c30615883fe40ab684e2f04fc8ed8665d5276&=&format=webp&quality=lossless"},
            {"name": "Barramundi", "base_price": 1000, "min_weight": 5.0, "max_weight": 15.0, "spawn_weight": 5, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445377123878699068/ikan_Barramundi.png?ex=69301fd8&is=692ece58&hm=4e63c985d260740a8532bb4dd768b36f738d475538b376c2bb22494dee3d9df0&=&format=webp&quality=lossless"},
            {"name": "Golden Dorado", "base_price": 700, "min_weight": 2.0, "max_weight": 10.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445377442809381035/ikan_Golden_Dorado.png?ex=69302024&is=692ecea4&hm=74ad8e4ae573442f9816a117756f12e8dc023a35148df901651f9c5a69243b99&=&format=webp&quality=lossless"},
            {"name": "Black Marlin", "base_price": 5000, "min_weight": 20.0, "max_weight": 80.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445377979193622628/bLACK_MARLIN.png?ex=693020a4&is=692ecf24&hm=8d7e1d9faaef625746aed93bc12c93987c7557d2d4ecbf5982050b17fec29798&=&format=webp&quality=lossless"},
            {"name": "Permit", "base_price": 550, "min_weight": 1.0, "max_weight": 5.0, "spawn_weight": 5, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445378377040269456/ikan_permit.png?ex=69302102&is=692ecf82&hm=419d217e7f03c46515ff9f9b68879a22877639e429015f66353edf949073185a&=&format=webp&quality=lossless"},
            {"name": "Barracuda", "base_price": 2000, "min_weight": 1.0, "max_weight": 6.0, "spawn_weight": 5, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445378535106547785/ikan_Barracuda.png?ex=69302128&is=692ecfa8&hm=f59fa714e4baf973512cfdffc7da1c89e347e85fc689bbf76b8b279063b871cd&=&format=webp&quality=lossless"},
            {"name": "Roosterfish", "base_price": 500, "min_weight": 2.0, "max_weight": 10.0, "spawn_weight": 4, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445379056773238804/Roosterfish.png?ex=693021a4&is=692ed024&hm=2b70983e0346b2dd79d64743d1440d3d2a862600f22a71a0604e4a321d08edfd&=&format=webp&quality=lossless"},
            {"name": "Sailfish", "base_price": 4500, "min_weight": 10.0, "max_weight": 60.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445379244430725281/Sailfish.png?ex=693021d1&is=692ed051&hm=94119ce09984b09bed11a090df25fabebba45f0175cd72b346e11abc0d2b0971&=&format=webp&quality=lossless"},
            {"name": "Red Drum", "base_price": 1500, "min_weight": 2.0, "max_weight": 15.0, "spawn_weight": 5, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445379493748277258/ikan_Red_Drum.png?ex=6930220d&is=692ed08d&hm=ae97c06a3d86ca0eb1dac9013383312b4a83e367ab7fc9e38978d97771f4d3ae&=&format=webp&quality=lossless"},
            {"name": "Tuna Sirip Kuning", "base_price": 5000, "min_weight": 10.0, "max_weight": 40.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445379823144009738/Tuna_Sirip_Kuning.png?ex=6930225b&is=692ed0db&hm=517b264a68ff86ceffa3dfaa136d01e830b7341a8252e88e882cc07481aacc11&=&format=webp&quality=lossless"}
        ],

        "Legendary": [
            {"name": "Mekong Giant Catfish", "base_price": 6000, "min_weight": 50.0, "max_weight": 300.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380001485689003/Mekong_Giant_Catfish.png?ex=69302286&is=692ed106&hm=359ccd5f2260a00f641dd5cdc53fe9ffc6f704fe349eaf4dea3848fb4cd3eb38&=&format=webp&quality=lossless"},
            {"name": "Arapaima Gigas", "base_price": 9000, "min_weight": 40.0, "max_weight": 200.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380240296902757/Arapaima_Gigas.png?ex=693022bf&is=692ed13f&hm=5a5de57bed01ee90e85a3127919f26c081c1c1694a8b2ac1a41c2e176b83d221&=&format=webp&quality=lossless"},
            {"name": "Blue Marlin", "base_price": 13000, "min_weight": 80.0, "max_weight": 300.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380445851226248/Blue_Marlin.png?ex=693022f0&is=692ed170&hm=aa1f4ca83e124fa62bd2e585f184d45b89561c9d34a0b4d824adc66ae93eb44c&=&format=webp&quality=lossless"},
            {"name": "Mola Mola", "base_price": 1500, "min_weight": 200.0, "max_weight": 1000.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380656367403100/Mola_Mola.png?ex=69302322&is=692ed1a2&hm=5123ec5a8a53d97dffcce7711c74d9ad6f59eb888776b820af5d72fcc4ec6a0e&=&format=webp&quality=lossless"},
            {"name": "Napoleon", "base_price": 10000, "min_weight": 5.0, "max_weight": 25.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380883803668551/ikan_Napoleon.png?ex=69302358&is=692ed1d8&hm=f3e400c46a8e6649d47b6cb188a87bf0a17df93db11a8431176e3c8d5903e512&=&format=webp&quality=lossless"},
            {"name": "Oarfish", "base_price": 12500, "min_weight": 20.0, "max_weight": 150.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381209411813396/Oarfish.png?ex=693023a6&is=692ed226&hm=cf155612ffba44e5c18a08af0c9684cd7972623baf439ca303ac2fea6c6418c6&=&format=webp&quality=lossless"},
            {"name": "Alligator Gar", "base_price": 5500, "min_weight": 10.0, "max_weight": 50.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381420200759498/Alligator_Gar.png?ex=693023d8&is=692ed258&hm=01d50aeedf38e8b599356993abec64b2540022fc84761bdd3120b091693b8173&=&format=webp&quality=lossless"},
            {"name": "Manta Ray", "base_price": 14500, "min_weight": 100.0, "max_weight": 500.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381657325604975/Giant_Stingray.png?ex=69302410&is=692ed290&hm=9e678e8be34f391bd7f287f7c38b9f3d26dc640e6b54c49395aca657a2f473a4&=&format=webp&quality=lossless"},
            {"name": "Giant Stingray", "base_price": 13000, "min_weight": 50.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381894790184991/Giant_Stingray.png?ex=69302449&is=692ed2c9&hm=e03c066f7ee0794cb4ce9f210c6ba04a0b71971eca7a5a21b37d8a6f2d0f9b0e&=&format=webp&quality=lossless"},
            {"name": "Hiu Martil", "base_price": 14500, "min_weight": 80.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382128668770324/Hiu_Martil.png?ex=69302481&is=692ed301&hm=d5b901ca9493960a0dffba7d282e089046d0e8edc2a366508b0758bc91611180&=&format=webp&quality=lossless"},
            {"name": "Hiu Macan", "base_price": 14000, "min_weight": 100.0, "max_weight": 500.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382414535884800/Hiu_Macan.png?ex=693024c5&is=692ed345&hm=71b89df8360057baca485c4090e0d5cb09bd5f0777657cfa8770423f0399c35f&=&format=webp&quality=lossless"},
            {"name": "Megalodon", "base_price": 20000, "min_weight": 8000.0, "max_weight": 30000.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445383272518651934/Megalodon.png?ex=69302592&is=692ed412&hm=bd3516d61f8352de5a84bf569adb7eeaaa586eb2d0653d635e87f055b517af49&=&format=webp&quality=lossless"},
            {"name": "Hiu Putih", "base_price": 15000, "min_weight": 100.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382645256294542/Great_White_Shark.png?ex=693024fc&is=692ed37c&hm=37fde9523241707a835e49b968fe72271807746ced52f20b1cc1658944a82d89&=&format=webp&quality=lossless"},
            {"name": "Gurita", "base_price": 4500, "min_weight": 1.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382907152695348/Gurita.png?ex=6930253a&is=692ed3ba&hm=edbaf2cdc6a5391b367c82f32c56063d80550a85c5175a07ed9f66518b59d6c2&=&format=webp&quality=lossless"}
        ],
}
        
        self.rarity_weights = {
            "Common": 50,
            "Uncommon": 30,
            "Rare": 15,
            "Epic": 4,
            "Legendary": 1
        }

        # Buff Item Data
        self.buff_item_data = {
            "Rokok Surya": {"price": 15000, "duration": 300, "description": "Cooldown Mancing -10s (5 Menit)", "emoji": "🚬", "type": "cooldown", "value": 10},
            "Kail Mata Dua": {"price": 20000, "duration": 300, "description": "20% Double Catch Chance (5 Menit)", "emoji": "🪝", "type": "double", "value": 20},
            "Pancing Magnet": {"price": 55000, "duration": 300, "description": "+10% Scrap & +3% Pearl Chance (5 Menit)", "emoji": "🧲", "type": "loot", "value": 15}
        }
        
        # Rod Data
        # weight_boost: Multiplier for fish weight (e.g. 1.1 = +10% weight)
        # rarity_boost: Flat percentage increase for higher rarities (Logic handled in catch)
        self.rod_data = {
            "Common Rod": {"price": 0, "weight_boost": 1.0, "rarity_boost": 0, "emoji": "🎣", "scaling_weight": 0.05, "scaling_rarity": 0},
            "Good Rod": {"price": 20000, "weight_boost": 1.1, "rarity_boost": 0, "emoji": "🎋", "scaling_weight": 0.05, "scaling_rarity": 0.1},
            "Unique Rod": {"price": 100000, "weight_boost": 1.3, "rarity_boost": 1, "emoji": "🔱", "scaling_weight": 0.1, "scaling_rarity": 0.1},
            "Masterwork Rod": {"price": 500000, "weight_boost": 1.5, "rarity_boost": 2, "emoji": "🌟", "scaling_weight": 0.1, "scaling_rarity": 0.2},
            "Dyto Rod": {"price": 2000000, "weight_boost": 2.0, "rarity_boost": 3, "emoji": "👑", "scaling_weight": 0.15, "scaling_rarity": 0.3}
        }

        # Forge Data (Costs & Risks)
        self.forge_data = {
            "Common Rod": {
                "tier": 1,
                "levels": {
                    1: {"rate": 100, "cost": 100, "scrap": 1, "pearl": 0, "risk": "none"},
                    2: {"rate": 90, "cost": 200, "scrap": 2, "pearl": 0, "risk": "none"},
                    3: {"rate": 80, "cost": 500, "scrap": 3, "pearl": 0, "risk": "none"},
                    4: {"rate": 75, "cost": 1000, "scrap": 5, "pearl": 0, "risk": "downgrade"},
                    5: {"rate": 70, "cost": 2000, "scrap": 8, "pearl": 0, "risk": "downgrade"},
                    6: {"rate": 60, "cost": 3500, "scrap": 10, "pearl": 0, "risk": "reset"},
                    7: {"rate": 50, "cost": 5000, "scrap": 15, "pearl": 0, "risk": "reset"},
                    8: {"rate": 40, "cost": 7500, "scrap": 20, "pearl": 0, "risk": "reset"},
                    9: {"rate": 30, "cost": 10000, "scrap": 0, "pearl": 1, "risk": "destroy"},
                    10: {"rate": 15, "cost": 15000, "scrap": 0, "pearl": 2, "risk": "destroy"}
                }
            },
            "Good Rod": {
                "tier": 2,
                "levels": {
                    1: {"rate": 100, "cost": 500, "scrap": 3, "pearl": 0, "risk": "none"},
                    2: {"rate": 90, "cost": 1000, "scrap": 5, "pearl": 0, "risk": "none"},
                    3: {"rate": 80, "cost": 2500, "scrap": 8, "pearl": 0, "risk": "none"},
                    4: {"rate": 70, "cost": 5000, "scrap": 10, "pearl": 0, "risk": "downgrade"},
                    5: {"rate": 60, "cost": 10000, "scrap": 15, "pearl": 0, "risk": "downgrade"},
                    6: {"rate": 50, "cost": 15000, "scrap": 20, "pearl": 0, "risk": "reset"},
                    7: {"rate": 40, "cost": 25000, "scrap": 30, "pearl": 0, "risk": "reset"},
                    8: {"rate": 30, "cost": 40000, "scrap": 0, "pearl": 1, "risk": "reset"},
                    9: {"rate": 20, "cost": 60000, "scrap": 0, "pearl": 2, "risk": "destroy"},
                    10: {"rate": 10, "cost": 100000, "scrap": 0, "pearl": 3, "risk": "destroy"}
                }
            },
            "Unique Rod": {
                "tier": 3,
                "levels": {
                    1: {"rate": 100, "cost": 2000, "scrap": 10, "pearl": 0, "risk": "none"},
                    2: {"rate": 85, "cost": 5000, "scrap": 20, "pearl": 0, "risk": "none"},
                    3: {"rate": 75, "cost": 10000, "scrap": 30, "pearl": 0, "risk": "none"},
                    4: {"rate": 65, "cost": 20000, "scrap": 50, "pearl": 0, "risk": "downgrade"},
                    5: {"rate": 55, "cost": 40000, "scrap": 75, "pearl": 0, "risk": "downgrade"},
                    6: {"rate": 45, "cost": 75000, "scrap": 0, "pearl": 1, "risk": "reset"},
                    7: {"rate": 35, "cost": 120000, "scrap": 0, "pearl": 2, "risk": "reset"},
                    8: {"rate": 25, "cost": 200000, "scrap": 0, "pearl": 3, "risk": "reset"},
                    9: {"rate": 15, "cost": 300000, "scrap": 0, "pearl": 5, "risk": "destroy"},
                    10: {"rate": 8, "cost": 500000, "scrap": 0, "pearl": 8, "risk": "destroy"}
                }
            },
            "Masterwork Rod": {
                "tier": 4,
                "levels": {
                    1: {"rate": 95, "cost": 5000, "scrap": 5, "pearl": 0, "risk": "none"},
                    2: {"rate": 85, "cost": 10000, "scrap": 10, "pearl": 0, "risk": "none"},
                    3: {"rate": 75, "cost": 20000, "scrap": 15, "pearl": 0, "risk": "none"},
                    4: {"rate": 65, "cost": 35000, "scrap": 25, "pearl": 0, "risk": "downgrade"},
                    5: {"rate": 55, "cost": 50000, "scrap": 0, "pearl": 1, "risk": "downgrade"},
                    6: {"rate": 45, "cost": 75000, "scrap": 0, "pearl": 2, "risk": "reset"},
                    7: {"rate": 35, "cost": 100000, "scrap": 0, "pearl": 3, "risk": "reset"},
                    8: {"rate": 25, "cost": 150000, "scrap": 0, "pearl": 4, "risk": "reset"},
                    9: {"rate": 15, "cost": 250000, "scrap": 0, "pearl": 6, "risk": "destroy"},
                    10: {"rate": 5, "cost": 400000, "scrap": 0, "pearl": 10, "risk": "destroy"}
                }
            },
            "Dyto Rod": {
                "tier": 5,
                "levels": {
                    1: {"rate": 90, "cost": 10000, "scrap": 0, "pearl": 1, "risk": "none"},
                    2: {"rate": 80, "cost": 25000, "scrap": 0, "pearl": 2, "risk": "none"},
                    3: {"rate": 70, "cost": 50000, "scrap": 0, "pearl": 3, "risk": "none"},
                    4: {"rate": 60, "cost": 75000, "scrap": 0, "pearl": 4, "risk": "downgrade"},
                    5: {"rate": 50, "cost": 100000, "scrap": 0, "pearl": 5, "risk": "downgrade"},
                    6: {"rate": 40, "cost": 200000, "scrap": 0, "pearl": 7, "risk": "reset"},
                    7: {"rate": 30, "cost": 350000, "scrap": 0, "pearl": 10, "risk": "reset"},
                    8: {"rate": 20, "cost": 500000, "scrap": 0, "pearl": 12, "risk": "reset"},
                    9: {"rate": 10, "cost": 750000, "scrap": 0, "pearl": 15, "risk": "destroy"},
                    10: {"rate": 3, "cost": 1000000, "scrap": 0, "pearl": 20, "risk": "destroy"}
                }
            }
        }



    def get_conn(self):
        return get_db_connection()

    def _init_db(self):
        conn = self.get_conn()
        if not conn:
            print("❌ Failed to connect to DB in Fishing init")
            return
            
        cursor = conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fish_inventory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    fish_name TEXT,
                    rarity TEXT,
                    weight DECIMAL(10, 2),
                    price INT,
                    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_rods (
                    user_id BIGINT,
                    rod_name VARCHAR(255),
                    level INT DEFAULT 0,
                    PRIMARY KEY (user_id, rod_name)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_profile (
                    user_id BIGINT PRIMARY KEY,
                    equipped_rod TEXT,
                    total_catches INT DEFAULT 0
                )
            ''')
            
            # Ensure fishing_profile default if created without default in previous schema 
            # (MySQL doesn't support ALTER COLUMN SET DEFAULT easily in one go if table exists, but CREATE handles new ones)

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_materials (
                    user_id BIGINT,
                    material_name VARCHAR(255),
                    amount INT DEFAULT 0,
                    PRIMARY KEY (user_id, material_name)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_items (
                    user_id BIGINT,
                    item_name VARCHAR(255),
                    amount INT DEFAULT 0,
                    PRIMARY KEY (user_id, item_name)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_buffs (
                    user_id BIGINT,
                    buff_name VARCHAR(255),
                    end_time TIMESTAMP,
                    PRIMARY KEY (user_id, buff_name)
                )
            ''')
            
            # Fishing Quests
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fishing_quests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    quest_type TEXT,
                    target_criteria TEXT,
                    target_value INT,
                    progress INT DEFAULT 0,
                    reward_amount INT,
                    is_claimed BOOLEAN DEFAULT 0,
                    created_at DATE,
                    quest_period TEXT,
                    expiration_date TIMESTAMP,
                    reward_type TEXT DEFAULT 'coin',
                    reward_name TEXT
                )
            ''')
            
            conn.commit()
            
            # Simple column addition checks (using try-except block for duplicate column error 1060)
            # MySQL error code for duplicate column is 1060
            
            # Check/Add total_catches to fishing_profile
            try:
                cursor.execute("DESCRIBE fishing_profile")
                cols = [row[0] for row in cursor.fetchall()]
                if 'total_catches' not in cols:
                    cursor.execute("ALTER TABLE fishing_profile ADD COLUMN total_catches INT DEFAULT 0")
            except Exception as e:
                print(f"Warning checking fishing_profile schema: {e}")

            # Check/Add level to fishing_rods
            try:
                cursor.execute("DESCRIBE fishing_rods")
                cols = [row[0] for row in cursor.fetchall()]
                if 'level' not in cols:
                    cursor.execute("ALTER TABLE fishing_rods ADD COLUMN level INT DEFAULT 0")
            except Exception as e:
                print(f"Warning checking fishing_rods schema: {e}")
                
            conn.commit()
            
        except mysql.connector.Error as err:
            print(f"❌ Database error in Fishing _init_db: {err}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def generate_quests(self, user_id):
        """Generate Daily and Weekly quests with variations"""
        conn = self.get_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor(buffered=True) # Use buffered cursor to avoid Unread result found
            now = datetime.now()
            
            # --- DAILY QUESTS (Reset at 12:00 PM) ---
            # If current time < 12:00 PM, today's quest day is effectively "yesterday" (or we haven't reached new day yet)
            # Logic: Calculate the expected "current daily reset time".
            # If now is 11:00 AM, the last reset was yesterday 12:00 PM.
            # If now is 1:00 PM, the last reset was today 12:00 PM.
            
            today_reset = now.replace(hour=12, minute=0, second=0, microsecond=0)
            if now < today_reset:
                current_daily_start = today_reset - timedelta(days=1)
            else:
                current_daily_start = today_reset
                
            daily_key = current_daily_start.strftime('%Y-%m-%d')
            
            cursor.execute('SELECT id FROM fishing_quests WHERE user_id = %s AND quest_period = %s AND created_at = %s', (user_id, 'daily', daily_key))
            if not cursor.fetchone():
                daily_templates = [
                    {"type": "catch_any", "criteria": "any", "min": 10, "max": 20, "reward_mult": 20},
                    {"type": "catch_rarity", "criteria": "Common", "min": 10, "max": 15, "reward_mult": 30},
                    {"type": "catch_rarity", "criteria": "Uncommon", "min": 5, "max": 10, "reward_mult": 50},
                    {"type": "catch_rarity", "criteria": "Rare", "min": 2, "max": 5, "reward_mult": 100},
                    {"type": "catch_weight", "criteria": "2", "min": 5, "max": 10, "reward_mult": 40}, # > 2kg
                    {"type": "catch_weight", "criteria": "5", "min": 2, "max": 5, "reward_mult": 80}, # > 5kg
                    {"type": "catch_weight", "criteria": "1", "min": 10, "max": 15, "reward_mult": 30}, # > 1kg
                    {"type": "total_weight", "criteria": "total", "min": 20, "max": 30, "reward_mult": 10},
                    {"type": "total_weight", "criteria": "total", "min": 40, "max": 50, "reward_mult": 10},
                    {"type": "catch_specific", "criteria": "Ikan Mas", "min": 5, "max": 5, "reward_mult": 50},
                    {"type": "catch_specific", "criteria": "Lele", "min": 5, "max": 5, "reward_mult": 50},
                    {"type": "catch_specific", "criteria": "Nila", "min": 5, "max": 5, "reward_mult": 50},
                    {"type": "catch_specific", "criteria": "Gurame", "min": 3, "max": 3, "reward_mult": 80},
                    {"type": "catch_specific", "criteria": "Patin", "min": 3, "max": 3, "reward_mult": 80},
                    {"type": "catch_specific", "criteria": "Bawal Hitam", "min": 3, "max": 3, "reward_mult": 80},
                ]
                
                selected_daily = random.sample(daily_templates, 5)
                # Expire at next reset
                expiry_daily = current_daily_start + timedelta(days=1)
                
                for quest in selected_daily:
                    target_val = random.randint(quest["min"], quest["max"])
                    
                    # Reward Logic (70% Coin, 30% Scrap Metal)
                    reward_type = 'coin'
                    reward_name = None
                    reward_amount = 0
                    
                    if random.random() < 0.30:
                        reward_type = 'material'
                        reward_name = 'Scrap Metal'
                        reward_amount = random.randint(1, 5)
                    else:
                        reward_amount = target_val * quest["reward_mult"] + random.randint(50, 200)
                    
                    cursor.execute('''
                        INSERT INTO fishing_quests (user_id, quest_type, target_criteria, target_value, reward_amount, reward_type, reward_name, is_claimed, created_at, quest_period, expiration_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, 'daily', %s)
                    ''', (user_id, quest["type"], quest["criteria"], target_val, reward_amount, reward_type, reward_name, daily_key, expiry_daily))
                    conn.commit() # Commit per batch or per insert

            # --- WEEKLY QUESTS (Reset Saturday) ---
            # Python weekday: Mon=0, Tue=1, ..., Fri=4, Sat=5, Sun=6
            # We want Saturday as the start of the week.
            # Calculate days since last Saturday.
            days_since_saturday = (now.weekday() - 5) % 7
            start_of_week_date = (now - timedelta(days=days_since_saturday)).replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_week = start_of_week_date.strftime('%Y-%m-%d')
            
            cursor.execute('SELECT id FROM fishing_quests WHERE user_id = %s AND quest_period = %s AND created_at = %s', (user_id, 'weekly', start_of_week))
            if not cursor.fetchone():
                weekly_templates = [
                    {"type": "catch_rarity", "criteria": "Legendary", "min": 3, "max": 5, "reward_mult": 2000},
                    {"type": "catch_rarity", "criteria": "Epic", "min": 10, "max": 15, "reward_mult": 500},
                    {"type": "catch_rarity", "criteria": "Rare", "min": 30, "max": 50, "reward_mult": 150},
                    {"type": "total_weight", "criteria": "total", "min": 300, "max": 400, "reward_mult": 20},
                    {"type": "total_weight", "criteria": "total", "min": 450, "max": 500, "reward_mult": 20},
                    {"type": "catch_weight", "criteria": "10", "min": 20, "max": 20, "reward_mult": 200}, # > 10kg x20
                    {"type": "catch_weight", "criteria": "50", "min": 5, "max": 5, "reward_mult": 500}, # > 50kg x5
                    {"type": "catch_any", "criteria": "any", "min": 300, "max": 300, "reward_mult": 30},
                    {"type": "catch_weight", "criteria": "100", "min": 1, "max": 2, "reward_mult": 2000}, # > 100kg
                    {"type": "total_weight", "criteria": "total", "min": 600, "max": 800, "reward_mult": 25}, 
                ]
                
                selected_weekly = random.sample(weekly_templates, 3)
                
                # Expire at next Saturday
                expiry_weekly = start_of_week_date + timedelta(days=7)
                
                for quest in selected_weekly:
                    target_val = random.randint(quest["min"], quest["max"])
                    
                    reward_type = 'coin'
                    reward_name = None
                    reward_amount = 0
                    
                    if random.random() < 0.40: # Higher chance for material in weekly
                        reward_type = 'material'
                        reward_name = 'Scrap Metal'
                        reward_amount = random.randint(5, 15)
                        if random.random() < 0.10: # Chance for Pearl
                            reward_name = "Magic Pearl"
                            reward_amount = 1
                    else:
                        reward_amount = target_val * quest["reward_mult"] + random.randint(500, 2000)
                        
                    cursor.execute('''
                        INSERT INTO fishing_quests (user_id, quest_type, target_criteria, target_value, reward_amount, reward_type, reward_name, is_claimed, created_at, quest_period, expiration_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, 'weekly', %s)
                    ''', (user_id, quest["type"], quest["criteria"], target_val, reward_amount, reward_type, reward_name, start_of_week, expiry_weekly))
                    conn.commit()

        except Exception as e:
            print(f"Error generating quests: {e}")
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def get_material(self, user_id, material_name):
        conn = self.get_conn()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT amount FROM fishing_materials WHERE user_id = %s AND material_name = %s', (user_id, material_name))
            res = cursor.fetchone()
            return res[0] if res else 0
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def add_material(self, user_id, material_name, amount):
        conn = self.get_conn()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            current = self.get_material(user_id, material_name)
            new_amount = current + amount
            if new_amount < 0: new_amount = 0
            
            cursor.execute('''
                INSERT INTO fishing_materials (user_id, material_name, amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount = %s
            ''', (user_id, material_name, new_amount, new_amount))
            conn.commit()
            return new_amount
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_rod_level(self, user_id, rod_name):
        conn = self.get_conn()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT level FROM fishing_rods WHERE user_id = %s AND rod_name = %s', (user_id, rod_name))
            res = cursor.fetchone()
            return res[0] if res else 0
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def update_rod_level(self, user_id, rod_name, new_level):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            if new_level < 0: new_level = 0
            
            # MySQL 'INSERT ... ON DUPLICATE KEY UPDATE' is better
            cursor.execute('''
                INSERT INTO fishing_rods (user_id, rod_name, level) 
                VALUES (%s, %s, %s) 
                ON DUPLICATE KEY UPDATE level = %s
            ''', (user_id, rod_name, new_level, new_level))
            conn.commit()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    # --- BUFF & ITEM HELPERS ---
    def add_item(self, user_id, item_name, amount):
        conn = self.get_conn()
        if not conn: return
        try:
            cursor = conn.cursor()
            # We can use ON DUPLICATE KEY UPDATE with amount = amount + VALUES(amount) or logic
            # Logic here: check existing first
            cursor.execute('SELECT amount FROM fishing_items WHERE user_id = %s AND item_name = %s', (user_id, item_name))
            res = cursor.fetchone()
            current = res[0] if res else 0
            new_amount = current + amount
            
            if new_amount <= 0:
                cursor.execute('DELETE FROM fishing_items WHERE user_id = %s AND item_name = %s', (user_id, item_name))
            else:
                cursor.execute('''
                    INSERT INTO fishing_items (user_id, item_name, amount) VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE amount = %s
                ''', (user_id, item_name, new_amount, new_amount))
            conn.commit()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
    
    def get_item_amount(self, user_id, item_name):
        conn = self.get_conn()
        if not conn: return 0
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT amount FROM fishing_items WHERE user_id = %s AND item_name = %s', (user_id, item_name))
            res = cursor.fetchone()
            return res[0] if res else 0
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def activate_buff(self, user_id, buff_name):
        data = self.buff_item_data.get(buff_name)
        if not data: return False
        
        duration = data['duration']
        end_time = datetime.now() + timedelta(seconds=duration)
        
        conn = self.get_conn()
        if not conn: return False
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO fishing_buffs (user_id, buff_name, end_time) VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE end_time = %s
            ''', (user_id, buff_name, end_time, end_time))
            conn.commit()
            return end_time
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def get_active_buffs(self, user_id):
        conn = self.get_conn()
        if not conn: return {}
        try:
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute('SELECT buff_name, end_time FROM fishing_buffs WHERE user_id = %s AND end_time > %s', (user_id, now))
            rows = cursor.fetchall()
            
            buffs = {}
            for name, end_ts in rows:
                if isinstance(end_ts, str):
                    try:
                        end_ts = datetime.fromisoformat(end_ts)
                    except:
                        continue 
                
                buffs[name] = {"end_time": end_ts, "data": self.buff_item_data.get(name)}
                
            return buffs
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    async def check_quest_progress(self, interaction, fish_name, rarity, weight):
        """Check and update quest progress (Daily & Weekly)"""
        user_id = interaction.user.id
        now = datetime.now()
        conn = self.get_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # Check active quests (not claimed, not expired)
            cursor.execute('''
                SELECT id, quest_type, target_criteria, target_value, progress 
                FROM fishing_quests 
                WHERE user_id = %s AND is_claimed = 0 AND (expiration_date IS NULL OR expiration_date > %s)
            ''', (user_id, now))
            
            active_quests = cursor.fetchall()
            
            completed_quests = []
            
            for q_id, q_type, criteria, target, progress in active_quests:
                if progress >= target:
                    continue
                    
                increment = 0
                if q_type == "catch_any":
                    increment = 1
                elif q_type == "catch_rarity" and criteria == rarity:
                    increment = 1
                elif q_type == "catch_weight" and weight >= float(criteria):
                    increment = 1
                elif q_type == "catch_specific" and criteria.lower() == fish_name.lower():
                    increment = 1
                elif q_type == "total_weight":
                    increment = max(1, int(weight)) 
                
                if increment > 0:
                    new_progress = progress + increment
                    cursor.execute('UPDATE fishing_quests SET progress = %s WHERE id = %s', (new_progress, q_id))
                    
                    if new_progress >= target:
                        completed_quests.append(q_id)
            
            conn.commit()
            
            if completed_quests:
                try:
                    await interaction.followup.send("🎉 **Quest Selesai!** Cek `/fish quests` untuk klaim hadiah.", ephemeral=True)
                except:
                    pass
        except Exception as e:
            print(f"Error checking quests: {e}")
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def get_economy(self):
        return self.bot.get_cog('Economy')

    async def send_raw_payload(self, interaction: discord.Interaction, payload: dict):
        url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        json_payload = {"type": 4, "data": payload}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_payload, headers=headers) as resp:
                if resp.status not in [200, 204]:
                    print(f"❌ Error sending Fishing payload: {resp.status} {await resp.text()}")

    def get_equipped_rod(self, user_id):
        conn = self.get_conn()
        if not conn: return "Common Rod" # Default fallback
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT equipped_rod FROM fishing_profile WHERE user_id = %s', (user_id,))
            res = cursor.fetchone()
            return res[0] if res else "Common Rod"
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def get_owned_rods(self, user_id):
        conn = self.get_conn()
        if not conn: return ["Common Rod"]
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT rod_name FROM fishing_rods WHERE user_id = %s', (user_id,))
            rows = cursor.fetchall()
            owned = [r[0] for r in rows]
            if "Common Rod" not in owned:
                owned.append("Common Rod")
            return owned
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    def get_weight_leaderboard(self):
        conn = self.get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, fish_name, weight, rarity 
                FROM fish_inventory 
                ORDER BY weight DESC 
                LIMIT 15
            ''')
            return cursor.fetchall()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_networth_leaderboard(self):
        conn = self.get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, SUM(price) as total_value 
                FROM fish_inventory 
                GROUP BY user_id 
                ORDER BY total_value DESC 
                LIMIT 15
            ''')
            return cursor.fetchall()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_top_fisher_leaderboard(self):
        conn = self.get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, total_catches 
                FROM fishing_profile 
                ORDER BY total_catches DESC 
                LIMIT 15
            ''')
            return cursor.fetchall()
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    async def give_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = ["Coin"]
        
        # Add Rods
        choices.extend(list(self.rod_data.keys()))
        
        # Add Buff Items
        choices.extend(list(self.buff_item_data.keys()))
        
        # Add Materials
        choices.extend(["Scrap Metal", "Magic Pearl"])
        
        return [
            app_commands.Choice(name=item, value=item)
            for item in choices if current.lower() in item.lower()
        ][:25]


    @app_commands.command(name="give", description="[ADMIN] Give items or coins to a user")
    @app_commands.describe(user="Target User", item="Item Name (or Coin)", amount="Amount")
    @app_commands.autocomplete(item=give_autocomplete)
    async def give(self, interaction: discord.Interaction, user: discord.Member, item: str, amount: int):
        # Admin Check
        if interaction.user.id != 719511161757761656:
            embed = discord.Embed(title="❌ Access Denied", description="Kamu tidak memiliki akses ke command ini!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if amount <= 0:
            embed = discord.Embed(title="❌ Invalid Amount", description="Jumlah harus lebih dari 0!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 1. COIN
        if item == "Coin":
            economy = self.bot.get_cog('Economy')
            if economy:
                new_balance = economy.update_balance(user.id, amount)
                embed = discord.Embed(
                    title="✅ Transaction Successful",
                    description=f"Berhasil memberikan **{amount:,} Coins** ke {user.mention}.",
                    color=discord.Color.green()
                )
                embed.add_field(name="New Balance", value=f"{new_balance:,} Coins", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(title="❌ System Error", description="Economy Cog not loaded.", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 2. RODS
        if item in self.rod_data:
            self.update_rod_level(user.id, item, amount)
            embed = discord.Embed(
                title="✅ Item Given",
                description=f"Berhasil memberikan **{item}** (Level {amount}) ke {user.mention}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 3. BUFF ITEMS
        if item in self.buff_item_data:
            self.add_item(user.id, item, amount)
            embed = discord.Embed(
                title="✅ Item Given",
                description=f"Berhasil memberikan **{amount}x {item}** ke {user.mention}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # 4. MATERIALS
        valid_materials = ["Scrap Metal", "Magic Pearl"]
        if item in valid_materials:
            self.add_material(user.id, item, amount)
            embed = discord.Embed(
                title="✅ Material Given",
                description=f"Berhasil memberikan **{amount}x {item}** ke {user.mention}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title="❌ Invalid Item", description=f"Item **{item}** tidak ditemukan.", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Define Group for /fish commands
    fish_group = app_commands.Group(name="fish", description="Fishing commands")

    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        user_id = interaction.user.id
        conn = self.get_conn()
        if not conn: return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT item_name, amount FROM fishing_items WHERE user_id = %s AND item_name LIKE %s", (user_id, f"%{current}%"))
            rows = cursor.fetchall()
            
            choices = []
            for name, amount in rows:
                label = f"{name} (x{amount})"
                choices.append(app_commands.Choice(name=label, value=name))
            
            return choices[:25]
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    @fish_group.command(name="use", description="Gunakan item buff")
    @app_commands.autocomplete(item=item_autocomplete)
    async def fish_use(self, interaction: discord.Interaction, item: str = None):
        user_id = interaction.user.id
        
        # If no item arg, show list
        if not item:
            # Check inventory
            conn = self.get_conn()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT item_name, amount FROM fishing_items WHERE user_id = %s', (user_id,))
                    rows = cursor.fetchall()
                    
                    if not rows:
                        await interaction.response.send_message("🎒 Tas item lu kosong!", ephemeral=True)
                        return
                    
                    opts = [discord.SelectOption(label=f"{name} (x{amt})", value=name) for name, amt in rows]
                    view = discord.ui.View()
                    select = discord.ui.Select(placeholder="Pilih item...", options=opts)
                    
                    async def callback(inter):
                        if inter.user.id != user_id: return
                        await self.process_use_item(inter, select.values[0])
                    
                    select.callback = callback
                    view.add_item(select)
                    await interaction.response.send_message("Pilih item untuk dipakai:", view=view, ephemeral=True)
                finally:
                    if conn.is_connected():
                        cursor.close()
                        conn.close()
        else:
            await self.process_use_item(interaction, item)

    async def process_use_item(self, interaction, item_name):
        # Allow fuzzy match logic if needed, currently exact match from select
        # Verify ownership
        amt = self.get_item_amount(interaction.user.id, item_name)
        if amt < 1:
            await interaction.response.send_message("❌ Lu gak punya item itu!", ephemeral=True)
            return

        end_time = self.activate_buff(interaction.user.id, item_name)
        if not end_time:
             await interaction.response.send_message("❌ Item tidak valid atau error.", ephemeral=True)
             return
             
        self.add_item(interaction.user.id, item_name, -1) # Consume
        ts = int(end_time.timestamp())
        await interaction.response.send_message(f"✅ **{item_name}** Aktif! Efek sampai <t:{ts}:R>.", ephemeral=True)

    @fish_group.command(name="buffs", description="Cek buff aktif")
    async def fish_buffs(self, interaction: discord.Interaction):
        buffs = self.get_active_buffs(interaction.user.id)
        if not buffs:
            await interaction.response.send_message("❌ Tidak ada buff aktif.", ephemeral=True)
            return
            
        embed = discord.Embed(title="🔥 Active Buffs", color=discord.Color.orange())
        for name, info in buffs.items():
            ts = int(info['end_time'].timestamp())
            data = info['data']
            embed.add_field(name=f"{data['emoji']} {name}", value=f"Ends <t:{ts}:R>\nEffect: {data['description']}", inline=False)
            
        await interaction.response.send_message(embed=embed)



    @fish_group.command(name="catch", description="Memancing ikan")
    async def catch(self, interaction: discord.Interaction):
        # 0. Manual Cooldown Logic to Support Buffs
        # Standard Cooldown: 15s. With Buff: 5s.
        user_id = interaction.user.id
        buffs = self.get_active_buffs(user_id)
        
        cooldown_duration = 15.0
        
        if "Rokok Surya" in buffs:
            cooldown_duration = 5.0 # -10s

        now = interaction.created_at.timestamp()
        last_time = self.catch_cooldowns.get(user_id, 0)
        
        if now - last_time < cooldown_duration:
            retry_after = cooldown_duration - (now - last_time)
            try:
                buff_msg = '(Buff Rokok Aktif 🚬)' if 'Rokok Surya' in buffs else ''
                await interaction.response.send_message(f"⏳ Hadeh... sabar **{retry_after:.1f}s** lagi! {buff_msg}", ephemeral=True)
            except:
                pass
            return
            
        self.catch_cooldowns[user_id] = now

        # 1. Get Equipped Rod and Stats
        equipped_rod = self.get_equipped_rod(user_id)
        rod_level = self.get_rod_level(user_id, equipped_rod)
        rod_stats = self.rod_data.get(equipped_rod, self.rod_data["Common Rod"])
        
        # Calculate Total Boosts
        base_weight_boost = rod_stats["weight_boost"]
        base_rarity_boost = rod_stats["rarity_boost"]
        scaling_weight = rod_stats.get("scaling_weight", 0.1)
        scaling_rarity = rod_stats.get("scaling_rarity", 1)
        
        weight_boost = base_weight_boost + (rod_level * scaling_weight)
        rarity_boost = base_rarity_boost + (rod_level * scaling_rarity)
        
        # Apply Buffs
        loot_boost = 0
        pearl_boost = 0
        if "Pancing Magnet" in buffs:
            loot_boost = 0.10
            pearl_boost = 0.03
            
        double_catch_chance = 0
        if "Kail Mata Dua" in buffs:
            double_catch_chance = 0.20
            
        # Determine number of fish (Double Catch)
        fish_count = 1
        is_double = False
        if random.random() < double_catch_chance:
            fish_count = 2
            is_double = True
            
        caught_items = []
        total_xp = 0 # Not used but good to track if needed
        
        for _ in range(fish_count):
            # 2. Rarity Roll
            rarities = list(self.rarity_weights.keys())
            rarity_weights = list(self.rarity_weights.values())
            
            if rarity_boost > 0:
                rarity_weights[2] += rarity_boost # Rare
                rarity_weights[3] += rarity_boost # Epic
                rarity_weights[4] += rarity_boost # Legendary
                
            rarity = random.choices(rarities, weights=rarity_weights, k=1)[0]
            
            # 3. Fish Roll
            fish_list = self.fish_data[rarity]
            fish_weights = [f["spawn_weight"] for f in fish_list]
            fish_info = random.choices(fish_list, weights=fish_weights, k=1)[0]
            
            name = fish_info["name"]
            image_url = fish_info.get("image_url") # Only last image used if double
            base_price = fish_info["base_price"]
            min_w = fish_info["min_weight"]
            max_w = fish_info["max_weight"]
            
            # 4. Weight & Price
            raw_weight = random.uniform(min_w, max_w)
            weight = round(raw_weight * weight_boost, 2)
            weight_multiplier = weight / min_w
            final_price = int(base_price * weight_multiplier)
            
            # Save
            conn = self.get_conn()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO fish_inventory (user_id, fish_name, rarity, weight, price)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (user_id, name, rarity, weight, final_price))
                    
                    caught_items.append({
                        "name": name, "rarity": rarity, "weight": weight, "price": final_price, "image": image_url
                    })
                    conn.commit()
                finally:
                     if conn.is_connected():
                        cursor.close()
                        conn.close()
            
            # Quest Check
            self.generate_quests(user_id) 
            await self.check_quest_progress(interaction, name, rarity, weight)

        # 5. Profile Update
        conn = self.get_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO fishing_profile (user_id, total_catches) 
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE total_catches = total_catches + %s
                ''', (user_id, fish_count, fish_count))
                conn.commit()
            finally:
                 if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        # 6. Material Drops
        material_msg = ""
        # Scrap: 10% + Buff
        scrap_chance = 0.10 + loot_boost
        if random.random() < scrap_chance:
            scrap_amount = random.randint(1, 3)
            self.add_material(user_id, "Scrap Metal", scrap_amount)
            material_msg = f"\n🔩 **{scrap_amount}x Scrap Metal**!"
            
        # Pearl: 1% + Buff (Rare+ only)
        # Check highest rarity caught
        best_rarity = "Common"
        priority = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
        for c in caught_items:
            if priority.index(c['rarity']) > priority.index(best_rarity):
                best_rarity = c['rarity']
                
        if best_rarity in ["Rare", "Epic", "Legendary"]:
            pearl_chance = 0.01 + pearl_boost
            if random.random() < pearl_chance:
                self.add_material(user_id, "Magic Pearl", 1)
                material_msg += f"\n🔮 **1x Magic Pearl**!"

        # 7. Embed
        # Restore "Main Fish" focus style
        main_fish = caught_items[0]
        
        color_map = {
            "Common": discord.Color.light_grey(),
            "Uncommon": discord.Color.green(),
            "Rare": discord.Color.blue(),
            "Epic": discord.Color.purple(),
            "Legendary": discord.Color.gold()
        }
        
        # Determine Title (Main Fish)
        # Classic Style: Just the fish name or "You caught x"
        # User said "not like before", likely means they prefer the stats in Fields, not Description.
        
        embed = discord.Embed(
            title=f"🎣 Hasil Pancingan",
            description=f"Kamu mendapatkan **{main_fish['name']}! **",
            color=color_map.get(main_fish['rarity'], discord.Color.default())
        )
        
        # Main Fish Details (Fields)
        embed.add_field(name="Rarity", value=f"{main_fish['rarity']}", inline=True)
        embed.add_field(name="Berat", value=f"{main_fish['weight']} kg", inline=True)
        embed.add_field(name="Harga", value=f"💰 {main_fish['price']}", inline=True)
        
        if main_fish['image']:
            embed.set_image(url=main_fish['image'])
            
        # Add Second Fish (Double Catch) if exists
        if len(caught_items) > 1:
            bonus_fish = caught_items[1]
            embed.add_field(name="✨ DOUBLE CATCH!", value=f"**{bonus_fish['name']}** ({bonus_fish['rarity']})\n{bonus_fish['weight']}kg | 💰 {bonus_fish['price']}", inline=False)
            
        # Materials
        if material_msg:
             embed.add_field(name="`📦 Extra Loot`", value=f"- {material_msg.strip()}", inline=True)
        
        # Footer Stats
        weight_bonus_pct = int((weight_boost - 1.0) * 100)
        footer_text = f"Rod: {equipped_rod} +{rod_level} | Bonus: +{weight_bonus_pct}% Weight"
        
        buff_icons = []
        if "Rokok Surya" in buffs: buff_icons.append("🚬")
        if "Kail Mata Dua" in buffs: buff_icons.append("⚓")
        if "Pancing Magnet" in buffs: buff_icons.append("🧲")
        
        if buff_icons:
            footer_text += f" | Buffs: {' '.join(buff_icons)}"
            
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed)


    @fish_group.command(name="inventory", description="Lihat hasil pancinganmu")
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        conn = self.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (interaction.user.id,))
            rows = cursor.fetchall()
            
            if not rows:
                await interaction.followup.send("🎒 Tas ikanmu kosong! Ayo memancing dulu.", ephemeral=True)
                return
                
            view = FishingInventoryView(self, interaction, rows)
            await view.send_initial_message()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
    @app_commands.command(name="fishing_rod", description="Equip your fishing rod")
    async def fishing_rod(self, interaction: discord.Interaction):
        view = RodEquipView(self, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @fish_group.command(name="shop", description="Buy better fishing rods")
    async def fish_shop(self, interaction: discord.Interaction):
        view = FishShopView(self, interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @fish_group.command(name="trade", description="Trade fish with another user")
    async def fish_trade(self, interaction: discord.Interaction, user: discord.User):
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot trade with yourself!", ephemeral=True)
            return
            
        if user.bot:
            await interaction.response.send_message("❌ You cannot trade with bots!", ephemeral=True)
            return

    @fish_group.command(name="quests", description="Lihat misi harian & mingguan fishing")
    async def fish_quests(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.generate_quests(interaction.user.id)
        
        conn = self.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
        
        try:
            cursor = conn.cursor()
            now = datetime.now()
            
            # Fetch Active Quests
            cursor.execute('''
                SELECT id, quest_type, target_criteria, target_value, progress, reward_amount, is_claimed, quest_period, reward_type, reward_name
                FROM fishing_quests 
                WHERE user_id = %s 
                AND (
                    (quest_period = 'daily' AND created_at = %s)
                    OR
                    (quest_period = 'weekly' AND created_at >= %s)
                )
            ''', (interaction.user.id, now.strftime('%Y-%m-%d'), (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')))
            
            quests = cursor.fetchall()
            
            embed = discord.Embed(title="📜 Fishing Quests", color=discord.Color.blue())
            
            daily_text = ""
            weekly_text = ""
            
            for q in quests:
                # q: 0:id, 1:type, 2:crit, 3:val, 4:prog, 5:rew_amt, 6:claimed, 7:period, 8:rew_type, 9:rew_name
                quest_id, q_type, crit, target, progress, reward, claimed, period, r_type, r_name = q
                
                status_icon = "✅" if claimed else "🔹"
                if progress >= target and not claimed: status_icon = "🎁"
                
                # Determine Item Name
                item_name = ""
                if q_type == "catch_specific":
                    item_name = crit
                elif q_type == "catch_rarity":
                    item_name = crit
                
                desc = f"{status_icon} **{self.format_quest_desc(q_type, crit, target)}**"
                desc += f"\n   Progress: `{min(progress, target)}/{target}`"
                
                reward_str = f"💰 {reward:,}"
                if r_type == 'item':
                    reward_str = f"📦 {reward}x {r_name}"
                elif r_type == 'material':
                    emoji = "🔩" if r_name == "Scrap Metal" else "🔮"
                    reward_str = f"{emoji} {reward}x {r_name}"
                    
                desc += f" | Reward: {reward_str}\n"
                
                if period == 'daily':
                    daily_text += desc
                else:
                    weekly_text += desc
            
            view = QuestClaimView(self, interaction.user.id, quests)
            
            if daily_text:
                embed.add_field(name="```📅 Daily Quests```", value=daily_text, inline=False)
            else:
                embed.add_field(name="```📅 Daily Quests```", value="*Tidak ada quest aktif.*", inline=False)
                
            if weekly_text:
                embed.add_field(name="```📅 Weekly Quests```", value=weekly_text, inline=False)
            else:
                embed.add_field(name="```📅 Weekly Quests```", value="*Tidak ada quest aktif.*", inline=False)
                
            await interaction.followup.send(embed=embed, view=view)
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    async def claim_quest_reward(self, interaction: discord.Interaction, quest_id: int):
        conn = self.get_conn()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT reward_amount, is_claimed, progress, target_value, reward_type, reward_name FROM fishing_quests WHERE id = %s', (quest_id,))
            res = cursor.fetchone()
            
            if not res:
                await interaction.response.send_message("❌ Quest tidak ditemukan!", ephemeral=True)
                return
                
            reward, is_claimed, progress, target, r_type, r_name = res
            
            if is_claimed:
                await interaction.response.send_message("❌ Quest sudah diklaim!", ephemeral=True)
                return
                
            if progress < target:
                await interaction.response.send_message("❌ Quest belum selesai!", ephemeral=True)
                return
                
            # Update DB
            cursor.execute('UPDATE fishing_quests SET is_claimed = 1 WHERE id = %s', (quest_id,))
            conn.commit()
            
            # Add Reward
            if r_type == 'material':
                self.add_material(interaction.user.id, r_name, reward)
                await interaction.response.send_message(f"🎉 **Selamat!** Kamu mendapatkan **{reward}x {r_name}**!", ephemeral=True)
            else:
                economy = self.get_economy()
                if economy:
                    economy.update_balance(interaction.user.id, reward)
                    await interaction.response.send_message(f"🎉 **Selamat!** Kamu mendapatkan 💰 **{reward}** koin!", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Economy system error.", ephemeral=True)
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()



    @fish_group.command(name="catalog", description="Show fishing catalog (Fish List)")
    async def catalog(self, interaction: discord.Interaction):
        payload = self.build_catalog_payload("Common")
        await self.send_raw_payload(interaction, payload)

    @fish_group.command(name="salvage", description="Salvage fish into materials (Scrap Metal)")
    async def salvage(self, interaction: discord.Interaction):
        conn = self.get_conn()
        if not conn:
             await interaction.response.send_message("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (interaction.user.id,))
            rows = cursor.fetchall()
            
            if not rows:
                await interaction.response.send_message("🎒 Tas ikanmu kosong! Tidak ada yang bisa di-salvage.", ephemeral=True)
                return
                
            view = FishingSalvageView(self, interaction, rows)
            await view.send_initial_message()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

    @fish_group.command(name="forge", description="Upgrade your fishing rod (Tempa)")
    async def forge(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            owned_rods = self.get_owned_rods(interaction.user.id)
            if not owned_rods:
                await interaction.followup.send("❌ Kamu belum memiliki pancingan!", ephemeral=True)
                return
                
            view = FishingForgeView(self, interaction, owned_rods)
            await view.send_initial_message()
        except Exception as e:
            print(f"[ERROR] /fish forge: {e}")
            await interaction.followup.send(f"❌ Terjadi kesalahan: {e}", ephemeral=True)



    def build_catalog_payload(self, rarity):
        fish_list = self.fish_data.get(rarity, [])
        
        content_text = f"## 📖 Fishing Catalog - {rarity}\n\n"
        if not fish_list:
            content_text += "*No fish found for this rarity.*"
        else:
            for fish in fish_list:
                name = fish["name"]
                price = fish["base_price"]
                min_w = fish["min_weight"]
                max_w = fish["max_weight"]
                spawn = fish["spawn_weight"]
                content_text += f"**{name}**\n💰 Base Price: {price}\n⚖️ Weight: {min_w}kg - {max_w}kg\n🎲 Chance: {spawn}\n\n"

        return {
            "flags": 32768,
            "components": [
                {
                    "type": 17, # Container
                    "components": [
                        {
                            "type": 10,
                            "content": "# 🎣 FISHING CATALOG"
                        },
                        {
                            "type": 14,
                            "spacing": 1
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 3, # Select Menu
                                    "custom_id": "fish_catalog_rarity_select",
                                    "options": [
                                        {"label": "Common", "value": "Common", "emoji": {"name": "⚪"}, "default": (rarity == "Common")},
                                        {"label": "Uncommon", "value": "Uncommon", "emoji": {"name": "🟢"}, "default": (rarity == "Uncommon")},
                                        {"label": "Rare", "value": "Rare", "emoji": {"name": "🔵"}, "default": (rarity == "Rare")},
                                        {"label": "Epic", "value": "Epic", "emoji": {"name": "🟣"}, "default": (rarity == "Epic")},
                                        {"label": "Legendary", "value": "Legendary", "emoji": {"name": "🟡"}, "default": (rarity == "Legendary")}
                                    ],
                                    "placeholder": "Select Rarity..."
                                }
                            ]
                        },
                        {
                            "type": 14,
                            "spacing": 1
                        },
                        {
                            "type": 10,
                            "content": content_text
                        }
                    ]
                }
            ]
        }

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id")
            
            if custom_id == "fish_catalog_rarity_select":
                selected = interaction.data["values"][0]
                payload = self.build_catalog_payload(selected)
                await self.update_raw_message(interaction, payload)

    async def update_raw_message(self, interaction: discord.Interaction, payload: dict):
        url = f"https://discord.com/api/v10/webhooks/{self.bot.user.id}/{interaction.token}/messages/@original"
        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
        
        # Type 7: Update Message
        json_payload = {"type": 7, "data": payload}
        
        callback_url = f"https://discord.com/api/v10/interactions/{interaction.id}/{interaction.token}/callback"
        async with aiohttp.ClientSession() as session:
            async with session.post(callback_url, json=json_payload, headers=headers) as resp:
                    if resp.status != 200:
                        print(f"Error updating message: {await resp.text()}")

    def cog_unload(self):
        # MySQL connection pooling handles connections, no single persistent conn to close
        pass

class FishingInventoryView(discord.ui.View):
    def __init__(self, cog, interaction, all_rows):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = interaction
        self.all_rows = all_rows
        self.page = 0
        self.items_per_page = 24
        self.max_pages = (len(all_rows) - 1) // self.items_per_page + 1
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        # Slicing for current page
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_rows = self.all_rows[start:end]
        
        # 1. Select Menu for Selling
        options = []
        
        # Removed Sell All from individual select to avoid clutter

        
        for i, (fid, name, rarity, weight, price) in enumerate(current_rows, start=1):
            # Visual ID is just the index in the list (1-25)
            visual_id = i 
            options.append(discord.SelectOption(
                label=f"{visual_id}. {name} ({weight}kg) - 💰{price}",
                description=f"Rarity: {rarity}",
                value=str(fid), # Value is still DB ID for logic
                emoji="🐟"
            ))
            
        select = discord.ui.Select(
            placeholder=f"Jual ikan (Halaman {self.page + 1}/{self.max_pages})...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        # 2. Bulk Action Select Menu
        bulk_options = [
            discord.SelectOption(label="💰 Jual SEMUA (Sell All)", value="sell_all", description="Jual semua ikan di inventory.", emoji="⚠️"),
            discord.SelectOption(label="⚪ Jual Common", value="sell_Common", description="Jual semua ikan Common.", emoji="🐟"),
            discord.SelectOption(label="🟢 Jual Uncommon", value="sell_Uncommon", description="Jual semua ikan Uncommon.", emoji="🐟"),
            discord.SelectOption(label="🔵 Jual Rare", value="sell_Rare", description="Jual semua ikan Rare.", emoji="🐟"),
            discord.SelectOption(label="🟣 Jual Epic", value="sell_Epic", description="Jual semua ikan Epic.", emoji="🐟"),
            discord.SelectOption(label="🟡 Jual Legendary", value="sell_Legendary", description="Jual semua ikan Legendary.", emoji="🐟"),
        ]
        
        bulk_select = discord.ui.Select(
            placeholder="Opsi Jual Rarity ...",
            min_values=1,
            max_values=1,
            options=bulk_options,
            row=1
        )
        bulk_select.callback = self.bulk_action_callback
        self.add_item(bulk_select)

        # 3. Navigation Buttons
        prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.page == 0), row=2)
        prev_btn.callback = self.prev_callback
        self.add_item(prev_btn)
        
        next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.page >= self.max_pages - 1), row=2)
        next_btn.callback = self.next_callback
        self.add_item(next_btn)

    async def send_initial_message(self):
        embed = self.build_embed()
        await self.original_interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self):
        total_value = sum(row[4] for row in self.all_rows)
        
        embed = discord.Embed(title=f"🎒 Tas Ikan {self.original_interaction.user.display_name}", color=discord.Color.blue())
        embed.set_footer(text=f"Total Ikan: {len(self.all_rows)} | Total Nilai: {total_value:,} koin | Halaman {self.page + 1}/{self.max_pages}")
        
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_rows = self.all_rows[start:end]
        
        desc = ""
        for i, (fid, name, rarity, weight, price) in enumerate(current_rows, start=1):
            desc += f"`{i}.` **{name}** ({rarity}) - {weight}kg - 💰{price}\n"
            
        embed.description = desc
        return embed

    async def prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("❌ Bukan tas ikanmu!", ephemeral=True)
            return
        
        if self.page > 0:
            self.page -= 1
            self.update_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("❌ Bukan tas ikanmu!", ephemeral=True)
            return
            
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("❌ Bukan tas ikanmu!", ephemeral=True)
            return
            
        selected_ids = interaction.data["values"]
        
        # Check for Sell All (Legacy check, kept for safety but removed from options)
        if "sell_all" in selected_ids:
            await self.sell_all_callback(interaction)
            return
        
        conn = self.cog.get_conn()
        if not conn:
             await interaction.response.send_message("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            
            total_price = 0
            count = 0
            
            for fid in selected_ids:
                cursor.execute('SELECT price FROM fish_inventory WHERE id = %s', (fid,))
                res = cursor.fetchone()
                if res:
                    total_price += res[0]
                    cursor.execute('DELETE FROM fish_inventory WHERE id = %s', (fid,))
                    count += 1
                    
            conn.commit()
            
            economy = self.cog.get_economy()
            if economy:
                economy.update_balance(interaction.user.id, total_price)
                
            await interaction.response.send_message(f"💰 Berhasil menjual **{count}** ikan seharga **{total_price:,}** koin!", ephemeral=True)
            
            # Refresh data and view
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (self.original_interaction.user.id,))
            self.all_rows = cursor.fetchall()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

        self.max_pages = (len(self.all_rows) - 1) // self.items_per_page + 1
        
        if self.page >= self.max_pages and self.page > 0:
            self.page = self.max_pages - 1
            
        self.update_components()
        await interaction.message.edit(embed=self.build_embed(), view=self)

    async def bulk_action_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("❌ Ini bukan inventory kamu!", ephemeral=True)
            return
            
        action = interaction.data["values"][0]
        
        if action == "sell_all":
            await self.sell_all_callback(interaction)
            return
            
        if action.startswith("sell_"):
            rarity = action.split("_")[1]
            
            # Calculate total for this rarity
            total_price = 0
            count = 0
            for row in self.all_rows:
                if row[2] == rarity:
                    total_price += row[4]
                    count += 1
            
            if count == 0:
                await interaction.response.send_message(f"❌ Tidak ada ikan **{rarity}** di inventory!", ephemeral=True)
                return
                
            confirm_view = ConfirmSellAllView(self, total_price, count, rarity)
            await interaction.response.send_message(f"⚠️ Yakin ingin menjual **SEMUA {rarity}** ({count} ikan) seharga **{total_price:,}** koin?", view=confirm_view, ephemeral=True)

    async def sell_all_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_interaction.user.id:
            await interaction.response.send_message("❌ Ini bukan inventory kamu!", ephemeral=True)
            return
            
        total_price = sum(row[4] for row in self.all_rows)
        count = len(self.all_rows)
        
        if count == 0:
            await interaction.response.send_message("❌ Inventory kamu kosong!", ephemeral=True)
            return
            
        # Confirm Dialog
        confirm_view = ConfirmSellAllView(self, total_price, count)
        await interaction.response.send_message(f"⚠️ Yakin ingin menjual **SEMUA** ({count} ikan) seharga **{total_price:,}** koin?", view=confirm_view, ephemeral=True)

class ConfirmSellAllView(discord.ui.View):
    def __init__(self, inventory_view, total_price, count, rarity=None):
        super().__init__(timeout=60)
        self.inventory_view = inventory_view
        self.total_price = total_price
        self.count = count
        self.rarity = rarity
        
    @discord.ui.button(label="✅ YA, JUAL", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        conn = self.inventory_view.cog.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
             
        try:
            # Update Economy
            economy = self.inventory_view.cog.get_economy()
            if economy:
                economy.update_balance(interaction.user.id, self.total_price)
                
            # Delete Fish
            cursor = conn.cursor()
            if self.rarity:
                cursor.execute('DELETE FROM fish_inventory WHERE user_id = %s AND rarity = %s', (interaction.user.id, self.rarity))
            else:
                cursor.execute('DELETE FROM fish_inventory WHERE user_id = %s', (interaction.user.id,))
                
            conn.commit()
            
            # Update Inventory View
            self.inventory_view.all_rows = [] 
            
            # Re-fetch to see what's left
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (interaction.user.id,))
            self.inventory_view.all_rows = cursor.fetchall()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
        
        self.inventory_view.page = 0
        self.inventory_view.max_pages = (len(self.inventory_view.all_rows) - 1) // self.inventory_view.items_per_page + 1
        if self.inventory_view.max_pages < 1: self.inventory_view.max_pages = 1
        
        self.inventory_view.update_components()
        
        try:
            await self.inventory_view.original_interaction.edit_original_response(embed=self.inventory_view.build_embed(), view=self.inventory_view)
        except:
            pass
        
        rarity_text = f" ({self.rarity})" if self.rarity else " SEMUA"
        await interaction.edit_original_response(content=f"✅ Berhasil menjual **{self.count}** ikan{rarity_text} seharga **{self.total_price:,}** koin!", view=None)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Penjualan dibatalkan.", view=None)

class TradeView(discord.ui.View):
    def __init__(self, cog, initiator, target, message=None):
        super().__init__(timeout=180)
        self.cog = cog
        self.initiator = initiator
        self.target = target
        self.message = message
        
        self.initiator_offer = [] # List of dicts
        self.target_offer = []
        
        self.initiator_ready = False
        self.target_ready = False
        
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # Add Fish Buttons
        btn_add_init = discord.ui.Button(label=f"➕ Add Fish ({self.initiator.name})", style=discord.ButtonStyle.secondary, row=0)
        btn_add_init.callback = self.add_fish_initiator
        self.add_item(btn_add_init)
        
        btn_add_target = discord.ui.Button(label=f"➕ Add Fish ({self.target.name})", style=discord.ButtonStyle.secondary, row=0)
        btn_add_target.callback = self.add_fish_target
        self.add_item(btn_add_target)

        # Remove Fish Buttons
        btn_rem_init = discord.ui.Button(label=f"➖ Remove ({self.initiator.name})", style=discord.ButtonStyle.secondary, row=1)
        btn_rem_init.callback = self.remove_fish_initiator
        self.add_item(btn_rem_init)
        
        btn_rem_target = discord.ui.Button(label=f"➖ Remove ({self.target.name})", style=discord.ButtonStyle.secondary, row=1)
        btn_rem_target.callback = self.remove_fish_target
        self.add_item(btn_rem_target)
        
        # Ready Button
        ready_label = "✅ Ready!" if (self.initiator_ready and self.target_ready) else "Ready?"
        ready_style = discord.ButtonStyle.success if (self.initiator_ready and self.target_ready) else discord.ButtonStyle.primary
        btn_ready = discord.ui.Button(label=ready_label, style=ready_style, row=2)
        btn_ready.callback = self.ready_callback
        self.add_item(btn_ready)
        
        # Cancel Button
        btn_cancel = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=2)
        btn_cancel.callback = self.cancel_callback
        self.add_item(btn_cancel)

    def build_embed(self):
        embed = discord.Embed(title="🤝 Fish Trade", color=discord.Color.gold())
        
        # Initiator Field
        init_status = "✅ READY" if self.initiator_ready else "⏳ Waiting..."
        init_desc = f"**Status:** {init_status}\n\n**Offer:**\n"
        if not self.initiator_offer:
            init_desc += "*Nothing*"
        else:
            for item in self.initiator_offer:
                init_desc += f"- {item['name']} ({item['weight']}kg) - {item['rarity']}\n"
        embed.add_field(name=f"👤 {self.initiator.name}", value=init_desc, inline=True)
        
        # Target Field
        target_status = "✅ READY" if self.target_ready else "⏳ Waiting..."
        target_desc = f"**Status:** {target_status}\n\n**Offer:**\n"
        if not self.target_offer:
            target_desc += "*Nothing*"
        else:
            for item in self.target_offer:
                target_desc += f"- {item['name']} ({item['weight']}kg) - {item['rarity']}\n"
        embed.add_field(name=f"👤 {self.target.name}", value=target_desc, inline=True)
        
        return embed

    async def add_fish_initiator(self, interaction: discord.Interaction):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("❌ This button is not for you!", ephemeral=True)
            return
        await self.open_inventory_select(interaction, self.initiator)

    async def add_fish_target(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ This button is not for you!", ephemeral=True)
            return
        await self.open_inventory_select(interaction, self.target)

    async def remove_fish_initiator(self, interaction: discord.Interaction):
        if interaction.user.id != self.initiator.id:
            await interaction.response.send_message("❌ This button is not for you!", ephemeral=True)
            return
        await self.open_remove_select(interaction, self.initiator)

    async def remove_fish_target(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ This button is not for you!", ephemeral=True)
            return
        await self.open_remove_select(interaction, self.target)

    async def open_remove_select(self, interaction: discord.Interaction, user):
        current_offer = self.initiator_offer if user.id == self.initiator.id else self.target_offer
        
        if not current_offer:
            await interaction.response.send_message("🎒 You haven't added any fish yet!", ephemeral=True)
            return
            
        view = TradeRemoveSelectView(self, user, current_offer)
        await interaction.response.send_message("Select fish to REMOVE from trade:", view=view, ephemeral=True)

    async def open_inventory_select(self, interaction: discord.Interaction, user):
        conn = self.cog.get_conn()
        if not conn:
             await interaction.response.send_message("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (user.id,))
            rows = cursor.fetchall()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
        
        if not rows:
            await interaction.response.send_message("🎒 Your inventory is empty!", ephemeral=True)
            return
            
        # Filter out already offered items
        current_offer_ids = [item['id'] for item in (self.initiator_offer if user.id == self.initiator.id else self.target_offer)]
        available_rows = [r for r in rows if r[0] not in current_offer_ids]
        
        if not available_rows:
            await interaction.response.send_message("🎒 No more fish to trade!", ephemeral=True)
            return

        view = TradeSelectView(self, user, available_rows[:25]) # Limit 25 for select menu
        await interaction.response.send_message("Select fish to add to trade:", view=view, ephemeral=True)

    async def ready_callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.initiator.id:
            self.initiator_ready = not self.initiator_ready
        elif interaction.user.id == self.target.id:
            self.target_ready = not self.target_ready
        else:
            await interaction.response.send_message("❌ You are not part of this trade!", ephemeral=True)
            return
            
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
        
        if self.initiator_ready and self.target_ready:
            await self.execute_trade(interaction)

    async def execute_trade(self, interaction):
        conn = self.cog.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            
            # Swap Owner
            for item in self.initiator_offer:
                cursor.execute('UPDATE fish_inventory SET user_id = %s WHERE id = %s', (self.target.id, item['id']))
                
            for item in self.target_offer:
                cursor.execute('UPDATE fish_inventory SET user_id = %s WHERE id = %s', (self.initiator.id, item['id']))
                
            conn.commit()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
        
        self.clear_items()
        embed = self.build_embed()
        embed.title = "✅ Trade Completed!"
        embed.color = discord.Color.green()
        await interaction.message.edit(embed=embed, view=None)
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in [self.initiator.id, self.target.id]:
            await interaction.response.send_message("❌ You cannot cancel this trade!", ephemeral=True)
            return
            
        self.clear_items()
        embed = self.build_embed()
        embed.title = "❌ Trade Cancelled"
        embed.color = discord.Color.red()
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class TradeSelectView(discord.ui.View):
    def __init__(self, trade_view, user, rows):
        super().__init__(timeout=60)
        self.trade_view = trade_view
        self.user = user
        
        options = []
        for fid, name, rarity, weight, price in rows:
            options.append(discord.SelectOption(
                label=f"{name} ({weight}kg)",
                description=f"Rarity: {rarity}",
                value=str(fid),
                emoji="🐟"
            ))
            
        select = discord.ui.Select(placeholder="Select fish to add...", options=options, max_values=len(options))
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_ids = interaction.data["values"]
        
        # Add to offer
        conn = self.trade_view.cog.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
        
        new_items = []
        try:
            cursor = conn.cursor()
            for fid in selected_ids:
                cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE id = %s', (fid,))
                row = cursor.fetchone()
                if row:
                    item = {"id": row[0], "name": row[1], "rarity": row[2], "weight": row[3], "price": row[4]}
                    new_items.append(item)
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
        
        if self.user.id == self.trade_view.initiator.id:
            self.trade_view.initiator_offer.extend(new_items)
            self.trade_view.initiator_ready = False # Reset ready
            self.trade_view.target_ready = False
        else:
            self.trade_view.target_offer.extend(new_items)
            self.trade_view.initiator_ready = False
            self.trade_view.target_ready = False
            
        # Update main view
        self.trade_view.update_buttons()
        # Update main view
        self.trade_view.update_buttons()
        if self.trade_view.message:
            await self.trade_view.message.edit(embed=self.trade_view.build_embed(), view=self.trade_view)
        elif self.trade_view.original_interaction:
            await self.trade_view.original_interaction.edit_original_response(embed=self.trade_view.build_embed(), view=self.trade_view)
        
        await interaction.followup.send(f"✅ Added {len(new_items)} fish to trade!", ephemeral=True)

class TradeRemoveSelectView(discord.ui.View):
    def __init__(self, trade_view, user, current_offer):
        super().__init__(timeout=60)
        self.trade_view = trade_view
        self.user = user
        
        options = []
        for item in current_offer:
            options.append(discord.SelectOption(
                label=f"{item['name']} ({item['weight']}kg)",
                description=f"Rarity: {item['rarity']}",
                value=str(item['id']),
                emoji="➖"
            ))
            
        select = discord.ui.Select(placeholder="Select fish to REMOVE...", options=options, max_values=len(options))
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_ids = interaction.data["values"]
        selected_ids = [int(i) for i in selected_ids]
        
        if self.user.id == self.trade_view.initiator.id:
            # Filter out removed items
            self.trade_view.initiator_offer = [item for item in self.trade_view.initiator_offer if item['id'] not in selected_ids]
            self.trade_view.initiator_ready = False
            self.trade_view.target_ready = False
        else:
            self.trade_view.target_offer = [item for item in self.trade_view.target_offer if item['id'] not in selected_ids]
            self.trade_view.initiator_ready = False
            self.trade_view.target_ready = False
            
        # Update main view
        self.trade_view.update_buttons()
        if self.trade_view.message:
            await self.trade_view.message.edit(embed=self.trade_view.build_embed(), view=self.trade_view)
        elif self.trade_view.original_interaction:
            await self.trade_view.original_interaction.edit_original_response(embed=self.trade_view.build_embed(), view=self.trade_view)
        
        await interaction.followup.send(f"✅ Removed {len(selected_ids)} fish from trade!", ephemeral=True)
        
class TradeChallengeView(discord.ui.View):
    def __init__(self, cog, initiator, target):
        super().__init__(timeout=60)
        self.cog = cog
        self.initiator = initiator
        self.target = target

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ This offer is not for you!", ephemeral=True)
            return
            
        # Start Trade
        view = TradeView(self.cog, self.initiator, self.target)
        embed = view.build_embed()
        await interaction.response.edit_message(content=f"🤝 Trade started!", embed=embed, view=view)
        view.message = interaction.message # Store message for updates

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ This offer is not for you!", ephemeral=True)
            return
            
        await interaction.response.edit_message(content=f"❌ {self.target.mention} declined the trade.", view=None)

class FishShopView(discord.ui.View):
    def __init__(self, cog, user, tab="rods"):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.tab = tab # 'rods' or 'items'
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # Tab Buttons
        # Use simple logic: if tab is active, use Primary style and disable? Or just keep enabled to allow toggle.
        # Common pattern: Active = Primary/Success, Inactive = Secondary
        style_rods = discord.ButtonStyle.primary if self.tab == "rods" else discord.ButtonStyle.secondary
        style_items = discord.ButtonStyle.primary if self.tab == "items" else discord.ButtonStyle.secondary
        
        self.add_item(ShopTabButton(label="🎣 Joran (Rods)", style=style_rods, custom_id="tab_rods", row=0))
        self.add_item(ShopTabButton(label="🎒 Buff & Items", style=style_items, custom_id="tab_items", row=0))
        
        # Content Selects
        if self.tab == "rods":
            self.add_item(ShopRodSelect(self.cog, self.user, row=1))
        else:
            self.add_item(ShopItemSelect(self.cog, self.user, row=1))

    def build_embed(self):
        embed = discord.Embed(title="🏪 Fishing Shop", color=discord.Color.gold())
        
        if self.tab == "rods":
            embed.description = "Upgrade pancinganmu biar makin gacor!"
            for rod, data in self.cog.rod_data.items():
                if rod == "Common Rod": continue
                owned = rod in self.cog.get_owned_rods(self.user.id)
                status = "✅ Dimiliki" if owned else f"💰 {data['price']:,}"
                
                embed.add_field(
                    name=f"{data['emoji']} {rod}",
                    value=f"**{status}**\nBoost: +{int((data['weight_boost']-1)*100)}% Weight, +{data['rarity_boost']} Rarity",
                    inline=False
                )
            
            # Lucky Charm & Pearl Info (Shown in Rods tab or separate? Maybe separate or bottom)
            # For simplicity, keep them in Rod/General tab or move to Items? 
            # User asked for "Tabs". Let's put specialized materials in Items tab maybe? 
            # Or keep Rods purely for Rods.
            # Let's put all "Materials" in Items tab.
            
        else:
            embed.description = "Item Buff & Material untuk mempermudah hidup pemancing!"
            
            # Buffs
            for item, data in self.cog.buff_item_data.items():
                 embed.add_field(
                    name=f"{data['emoji']} {item}",
                    value=f"💰 **{data['price']:,}**\n⏱️ {data['duration']//60} Menit\nℹ️ {data['description']}",
                    inline=False
                )
            
            embed.add_field(name="──────────────", value="**Special Items**", inline=False)
            
            # Special Items hardcoded for now or from data
            embed.add_field(name="🍀 Lucky Charm", value="💰 **100,000**\nEffect: +50% Forge Rate", inline=True)
            embed.add_field(name="🔮 Magic Pearl", value="💰 **250,000**\nEffect: Forge Material", inline=True)
            
        # Balance Footer
        economy = self.cog.get_economy()
        bal = economy.get_balance(self.user.id) if economy else 0
        embed.set_footer(text=f"Saldo Anda: {bal:,} coins")
        
        return embed

class ShopTabButton(discord.ui.Button):
    def __init__(self, label, style, custom_id, row):
        super().__init__(label=label, style=style, custom_id=custom_id, row=row)

    async def callback(self, interaction: discord.Interaction):
        view: FishShopView = self.view
        if view.user.id != interaction.user.id:
            await interaction.response.send_message("❌ Ini bukan sesi shop kamu!", ephemeral=True)
            return
        
        view.tab = "rods" if self.custom_id == "tab_rods" else "items"
        view.update_buttons()
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

class ShopItemSelect(discord.ui.Select):
    def __init__(self, cog, user, row):
        options = []
        # Buffs
        for item, data in cog.buff_item_data.items():
            options.append(discord.SelectOption(
                label=item,
                description=f"💰 {data['price']:,} - {data['description']}",
                value=item,
                emoji=data['emoji']
            ))
            
        # Special Items
        options.append(discord.SelectOption(label="Lucky Charm", description="💰 100,000 - Increase Forge Chance", value="Lucky Charm", emoji="🍀"))
        options.append(discord.SelectOption(label="Magic Pearl", description="💰 250,000 - Forge Material", value="Magic Pearl", emoji="🔮"))
            
        super().__init__(placeholder="Pilih item untuk dibeli...", min_values=1, max_values=1, options=options, row=row)
        self.cog = cog
        self.user_obj = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_obj.id:
            await interaction.response.send_message("❌ Not your session!", ephemeral=True)
            return

        item_name = self.values[0]
        price = 0
        is_buff = False
        
        if item_name in self.cog.buff_item_data:
            price = self.cog.buff_item_data[item_name]['price']
            is_buff = True
        elif item_name == "Lucky Charm":
            price = 100000
        elif item_name == "Magic Pearl":
            price = 250000
        
        economy = self.cog.get_economy()
        if not economy:
             await interaction.response.send_message("❌ Economy system error.", ephemeral=True)
             return

        bal = economy.get_balance(interaction.user.id)
        
        if bal < price:
            await interaction.response.send_message(f"❌ Duit lu kurang bos! Butuh {price:,}", ephemeral=True)
            return

        economy.update_balance(interaction.user.id, -price)
        
        if is_buff:
            self.cog.add_item(interaction.user.id, item_name, 1)
        else:
            self.cog.add_material(interaction.user.id, item_name, 1)
        
        await interaction.response.send_message(f"✅ Berhasil membeli **{item_name}**!", ephemeral=True)
        # Refresh View (Balance update)
        await interaction.message.edit(embed=self.view.build_embed(), view=self.view)

class ShopRodSelect(discord.ui.Select):
    def __init__(self, cog, user, row):
        options = []
        for rod, data in cog.rod_data.items():
            if rod == "Common Rod": continue
            options.append(discord.SelectOption(
                label=rod,
                description=f"Price: {data['price']:,}",
                value=rod,
                emoji=data['emoji']
            ))
        super().__init__(placeholder="Pilih joran untuk dibeli...", min_values=1, max_values=1, options=options, row=row)
        self.cog = cog
        self.user_obj = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_obj.id:
            return await interaction.response.send_message("❌ This is not your shop interaction!", ephemeral=True)
        
        rod_name = self.values[0]
        rod_data = self.cog.rod_data[rod_name]
        price = rod_data["price"]
        
        # Check if owned
        owned = self.cog.get_owned_rods(interaction.user.id)
        if rod_name in owned:
            return await interaction.response.send_message("❌ You already own this rod!", ephemeral=True)
            
        economy = self.cog.get_economy()
        if not economy:
            return await interaction.response.send_message("❌ Economy system not loaded.", ephemeral=True)
            
        bal = economy.get_balance(interaction.user.id)
        if bal < price:
             return await interaction.response.send_message("❌ Insufficient funds!", ephemeral=True)
             
        economy.update_balance(interaction.user.id, -price)
        
        conn = self.cog.get_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO fishing_rods (user_id, rod_name) VALUES (%s, %s)", (interaction.user.id, rod_name))
                conn.commit()
            finally:
                 if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        await interaction.response.send_message(f"✅ Successfully bought **{rod_name}**!", ephemeral=True)
        await interaction.message.edit(embed=self.view.build_embed(), view=self.view)

class RodEquipView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        owned_rods = self.cog.get_owned_rods(self.user.id)
        equipped = self.cog.get_equipped_rod(self.user.id)
        
        options = []
        for rod_name in owned_rods:
            stats = self.cog.rod_data.get(rod_name, self.cog.rod_data["Common Rod"])
            is_equipped = rod_name == equipped
            
            label = f"{rod_name} (Equipped)" if is_equipped else rod_name
            
            options.append(discord.SelectOption(
                label=label,
                description=f"Weight x{stats['weight_boost']} | Rarity +{stats['rarity_boost']}%",
                value=rod_name,
                emoji=stats["emoji"],
                default=is_equipped
            ))
            
        select = discord.ui.Select(placeholder="Equip a rod...", options=options)
        select.callback = self.callback
        self.add_item(select)

    def build_embed(self):
        equipped = self.cog.get_equipped_rod(self.user.id)
        level = self.cog.get_rod_level(self.user.id, equipped)
        stats = self.cog.rod_data.get(equipped, self.cog.rod_data["Common Rod"])
        
        # Calculate Stats with Level
        base_weight = stats["weight_boost"]
        base_rarity = stats["rarity_boost"]
        scaling_weight = stats.get("scaling_weight", 0.1)
        scaling_rarity = stats.get("scaling_rarity", 1)
        
        final_weight = base_weight + (level * scaling_weight)
        final_rarity = base_rarity + (level * scaling_rarity)
        
        embed = discord.Embed(title="🎒 Equipment", color=discord.Color.blue())
        embed.add_field(name="Current Rod", value=f"{stats['emoji']} **{equipped} +{level}**", inline=False)
        embed.add_field(name="Stats", value=f"Weight Boost: **x{final_weight:.1f}**\nRarity Boost: **+{final_rarity}%**", inline=False)
        return embed

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This menu is not for you!", ephemeral=True)
            return
            
        rod_name = interaction.data["values"][0]
        
        conn = self.cog.get_conn()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO fishing_profile (user_id, equipped_rod) VALUES (%s, %s) ON DUPLICATE KEY UPDATE equipped_rod = %s', (self.user.id, rod_name, rod_name))
                conn.commit()
            finally:
                 if conn.is_connected():
                    cursor.close()
                    conn.close()
        
        await interaction.response.send_message(f"✅ Equipped **{rod_name}**!", ephemeral=True)
        
        self.update_components()
        await interaction.message.edit(embed=self.build_embed(), view=self)

class FishLeaderboardView(discord.ui.View):
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.mode = "weight" # weight or networth
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        options = [
            discord.SelectOption(label="🏆 Heaviest Fish (Weight)", value="weight", description="Top 15 Heaviest Fish", emoji="⚖️", default=(self.mode == "weight")),
            discord.SelectOption(label="💰 Richest Fisher (Networth)", value="networth", description="Top 15 Highest Inventory Value", emoji="💎", default=(self.mode == "networth"))
        ]
        
        select = discord.ui.Select(placeholder="Select Leaderboard Category...", options=options)
        select.callback = self.callback
        self.add_item(select)

    def build_embed(self):
        if self.mode == "weight":
            title = "🏆 Fishing Leaderboard - Heaviest Fish"
            data = self.cog.get_weight_leaderboard()
            # data: [(user_id, fish_name, weight, rarity), ...]
        else:
            title = "💎 Fishing Leaderboard - Networth"
            data = self.cog.get_networth_leaderboard()
            # data: [(user_id, total_value), ...]
            
        embed = discord.Embed(title=title, color=discord.Color.gold())
        
        desc = ""
        if not data:
            desc = "TBD (No data yet)"
        else:
            for i, row in enumerate(data, start=1):
                user_id = row[0]
                user = self.cog.bot.get_user(user_id)
                username = user.name if user else f"User {user_id}"
                
                if self.mode == "weight":
                    fish_name, weight, rarity = row[1], row[2], row[3]
                    desc += f"`{i}.` **{username}** - {fish_name} ({weight}kg) [{rarity}]\n"
                else:
                    total_value = row[1]
                    desc += f"`{i}.` **{username}** - 💰 {total_value:,}\n"
                    
        embed.description = desc
        return embed

    async def callback(self, interaction: discord.Interaction):
        self.mode = interaction.data["values"][0]
        self.original_interaction = interaction
        self.owned_rods = owned_rods
        self.selected_rod = None
        self.use_lucky_charm = False
        self.last_result = None # Store result message
        self.last_status = None # Store result status (success/failure) for color
        
        self.update_components()

class FishingForgeView(discord.ui.View):
    def __init__(self, cog, interaction, owned_rods):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = interaction
        self.owned_rods = owned_rods
        self.selected_rod = None
        self.use_lucky_charm = False
        self.last_result = None # Store result message
        self.last_status = None # Store result status (success/failure) for color
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        # Select Rod
        options = []
        for rod_name in self.owned_rods:
            level = self.cog.get_rod_level(self.original_interaction.user.id, rod_name)
            
            # Safe access to rod data
            rod_data = self.cog.rod_data.get(rod_name, {})
            emoji = rod_data.get("emoji", "🎣")
            
            label = f"{rod_name} +{level}"
            if level >= 10:
                label += " (MAX)"
                
            options.append(discord.SelectOption(
                label=label,
                value=rod_name,
                emoji=emoji,
                default=(rod_name == self.selected_rod)
            ))
            
        select = discord.ui.Select(placeholder="Pilih Rod untuk ditempa...", options=options)
        select.callback = self.select_callback
        self.add_item(select)
        
        # Forge Button & Lucky Charm Toggle
        if self.selected_rod:
            level = self.cog.get_rod_level(self.original_interaction.user.id, self.selected_rod)
            if level < 10:
                # Lucky Charm Toggle
                charm_label = "🍀 Lucky Charm: ON" if self.use_lucky_charm else "🍀 Lucky Charm: OFF"
                charm_style = discord.ButtonStyle.success if self.use_lucky_charm else discord.ButtonStyle.secondary
                btn_charm = discord.ui.Button(label=charm_label, style=charm_style)
                btn_charm.callback = self.charm_callback
                self.add_item(btn_charm)
                
                btn_forge = discord.ui.Button(label="🔨 TEMPA!", style=discord.ButtonStyle.danger)
                btn_forge.callback = self.forge_callback
                self.add_item(btn_forge)

    async def charm_callback(self, interaction: discord.Interaction):
        # Check if user has charm
        user_charm = self.cog.get_material(interaction.user.id, "Lucky Charm")
        if not self.use_lucky_charm and user_charm <= 0:
            await interaction.response.send_message("❌ Kamu tidak punya Lucky Charm! Beli di shop.", ephemeral=True)
            return
            
        self.use_lucky_charm = not self.use_lucky_charm
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def send_initial_message(self):
        embed = discord.Embed(title="⚒️ Blacksmith Forge", description="Pilih pancingan yang ingin kamu upgrade.", color=discord.Color.dark_grey())
        await self.original_interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_rod = interaction.data["values"][0]
        self.last_result = None # Reset result on new selection
        self.last_status = None # Reset status
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    def build_embed(self):
        if not self.selected_rod:
            return discord.Embed(title="⚒️ Blacksmith Forge", description="Pilih pancingan yang ingin kamu upgrade.", color=discord.Color.dark_grey())
            
        level = self.cog.get_rod_level(self.original_interaction.user.id, self.selected_rod)
        
        # Determine Color
        color = discord.Color.dark_red()
        if self.last_status == "success":
            color = discord.Color.green()
        elif self.last_status == "failure":
            color = discord.Color.red()
            
        # Base Embed
        embed = discord.Embed(title=f"⚒️ Upgrade {self.selected_rod}", color=color)
        
        # Add Last Result if exists
        if self.last_result:
            embed.description = self.last_result
            
        if level >= 10:
             embed.title += f" +{level} (MAX)"
             embed.add_field(name="Status", value="✅ Rod ini sudah mencapai level maksimal!", inline=False)
             return embed

        next_level = level + 1
        forge_info = self.cog.forge_data[self.selected_rod]["levels"][next_level]
        
        cost = forge_info["cost"]
        rate = forge_info["rate"]
        scrap = forge_info["scrap"]
        pearl = forge_info["pearl"]
        risk = forge_info["risk"]
        
        # Apply Lucky Charm Boost
        if self.use_lucky_charm:
            rate += 50 # +50% Success Rate
            if rate > 100: rate = 100
        
        risk_text = "Aman"
        if risk == "downgrade": risk_text = "Turun 1 Level"
        elif risk == "reset": risk_text = "Reset ke +0"
        elif risk == "destroy": risk_text = "HANCUR 💀"
        
        embed.title += f" (+{level} ➡️ +{next_level})"
        embed.add_field(name="💰 Biaya", value=f"{cost:,} Coins", inline=True)
        
        rate_text = f"{rate}%"
        if self.use_lucky_charm:
            rate_text += " (🍀 Boosted)"
        embed.add_field(name="🎲 Peluang Sukses", value=rate_text, inline=True)
        
        embed.add_field(name="⚠️ Risiko Gagal", value=risk_text, inline=True)
        
        materials = []
        if scrap > 0: materials.append(f"{scrap}x Scrap Metal 🔩")
        if pearl > 0: materials.append(f"{pearl}x Magic Pearl 🔮")
        if self.use_lucky_charm: materials.append("1x Lucky Charm 🍀")
        
        embed.add_field(name="📦 Material Dibutuhkan", value="\n".join(materials) if materials else "None", inline=False)
        
        # User Resources
        user_scrap = self.cog.get_material(self.original_interaction.user.id, "Scrap Metal")
        user_pearl = self.cog.get_material(self.original_interaction.user.id, "Magic Pearl")
        user_charm = self.cog.get_material(self.original_interaction.user.id, "Lucky Charm")
        economy = self.cog.get_economy()
        user_bal = economy.get_balance(self.original_interaction.user.id) if economy else 0
        
        embed.set_footer(text=f"Resources: 💰{user_bal:,} | 🔩{user_scrap} | 🔮{user_pearl} | 🍀{user_charm}")
        
        return embed

    async def forge_callback(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            rod_name = self.selected_rod
            
            if not rod_name:
                await interaction.response.send_message("❌ Pilih rod terlebih dahulu!", ephemeral=True)
                return

            level = self.cog.get_rod_level(user_id, rod_name)
            next_level = level + 1
            
            # Validate Forge Data
            if rod_name not in self.cog.forge_data or next_level not in self.cog.forge_data[rod_name]["levels"]:
                 await interaction.response.send_message("❌ Data forge tidak ditemukan atau level sudah maksimal!", ephemeral=True)
                 return
                 
            forge_info = self.cog.forge_data[rod_name]["levels"][next_level]
            
            cost = forge_info["cost"]
            scrap = forge_info["scrap"]
            pearl = forge_info["pearl"]
            rate = forge_info["rate"]
            risk = forge_info["risk"]
            
            # Apply Lucky Charm Boost
            if self.use_lucky_charm:
                rate += 50
                if rate > 100: rate = 100
            
            # Check Resources
            economy = self.cog.get_economy()
            if not economy:
                await interaction.response.send_message("❌ Economy Error.", ephemeral=True)
                return
                
            bal = economy.get_balance(user_id)
            user_scrap = self.cog.get_material(user_id, "Scrap Metal")
            user_pearl = self.cog.get_material(user_id, "Magic Pearl")
            user_charm = self.cog.get_material(user_id, "Lucky Charm")
            
            if bal < cost:
                await interaction.response.send_message(f"❌ Uang tidak cukup! Butuh {cost:,} coins.", ephemeral=True)
                return
            if user_scrap < scrap:
                await interaction.response.send_message(f"❌ Scrap Metal kurang! Butuh {scrap}x.", ephemeral=True)
                return
            if user_pearl < pearl:
                await interaction.response.send_message(f"❌ Magic Pearl kurang! Butuh {pearl}x.", ephemeral=True)
                return
            if self.use_lucky_charm and user_charm < 1:
                 await interaction.response.send_message("❌ Lucky Charm kurang!", ephemeral=True)
                 return
                
            # Deduct Resources
            economy.update_balance(user_id, -cost)
            self.cog.add_material(user_id, "Scrap Metal", -scrap)
            self.cog.add_material(user_id, "Magic Pearl", -pearl)
            if self.use_lucky_charm:
                self.cog.add_material(user_id, "Lucky Charm", -1)
            
            # Roll RNG
            roll = random.randint(1, 100)
            success = roll <= rate
            
            print(f"[DEBUG] Forge: User={interaction.user.name}, Rod={rod_name}, Level={level}->{next_level}, Rate={rate}, Roll={roll}, Success={success}")
            
            if success:
                self.cog.update_rod_level(user_id, rod_name, next_level)
                self.last_result = f"🔥 **SUKSES!** {rod_name} naik ke level **+{next_level}**!"
                self.last_status = "success"
            else:
                # Failure Logic
                result_text = "Gagal! Level tetap."
                if risk == "downgrade":
                    new_level = max(0, level - 1)
                    self.cog.update_rod_level(user_id, rod_name, new_level)
                    result_text = f"Gagal! Level turun menjadi **+{new_level}**."
                elif risk == "reset":
                    self.cog.update_rod_level(user_id, rod_name, 0)
                    result_text = "Gagal! Level **RESET** ke +0."
                elif risk == "destroy":
                    conn = self.cog.get_conn()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute('DELETE FROM fishing_rods WHERE user_id = %s AND rod_name = %s', (user_id, rod_name))
                            
                            # Check if equipped, if so, equip Common Rod
                            equipped = self.cog.get_equipped_rod(user_id)
                            if equipped == rod_name:
                                cursor.execute('UPDATE fishing_profile SET equipped_rod = %s WHERE user_id = %s', ("Common Rod", user_id))
                                
                            conn.commit()
                        finally:
                             if conn.is_connected():
                                cursor.close()
                                conn.close()
                    
                    result_text = "💥 **GAGAL TOTAL!** Rod **HANCUR** berkeping-keping! 💀"
                    self.selected_rod = None # Reset selection
                    
                self.last_result = f"💀 **GAGAL!** {result_text}"
                self.last_status = "failure"
                
            # Reset Lucky Charm usage
            if self.use_lucky_charm:
                self.use_lucky_charm = False
                
            # Refresh View
            self.update_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
            
        except Exception as e:
            print(f"[ERROR] Forge Callback: {e}")
            try:
                await interaction.followup.send(f"❌ Terjadi kesalahan: {e}", ephemeral=True)
            except:
                pass



class ConfirmSalvageView(discord.ui.View):
    def __init__(self, salvage_view, selected_ids, total_scrap, count, rarity=None):
        super().__init__(timeout=60)
        self.salvage_view = salvage_view
        self.selected_ids = selected_ids
        self.total_scrap = total_scrap
        self.count = count
        self.rarity = rarity
        
    @discord.ui.button(label="✅ YA, SALVAGE", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        conn = self.salvage_view.cog.get_conn()
        if not conn:
             await interaction.followup.send("❌ Database Error", ephemeral=True)
             return
             
        try:
            cursor = conn.cursor()
            
            # Execute Deletion
            if self.selected_ids:
                for fid in self.selected_ids:
                     cursor.execute('DELETE FROM fish_inventory WHERE id = %s', (fid,))
            elif self.rarity:
                cursor.execute('DELETE FROM fish_inventory WHERE user_id = %s AND rarity = %s', (self.salvage_view.original_interaction.user.id, self.rarity))
            else:
                # Salvage All
                cursor.execute('DELETE FROM fish_inventory WHERE user_id = %s', (self.salvage_view.original_interaction.user.id,))
                 
            conn.commit()
            
            self.salvage_view.cog.add_material(interaction.user.id, "Scrap Metal", self.total_scrap)
            
            # Update Parent View
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (self.salvage_view.original_interaction.user.id,))
            self.salvage_view.all_rows = cursor.fetchall()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()
        
        self.salvage_view.max_pages = (len(self.salvage_view.all_rows) - 1) // self.salvage_view.items_per_page + 1
        if self.salvage_view.page >= self.salvage_view.max_pages: self.salvage_view.page = max(0, self.salvage_view.max_pages - 1)
        
        self.salvage_view.update_components()
        
        try:
            await self.salvage_view.original_interaction.edit_original_response(embed=self.salvage_view.build_embed(), view=self.salvage_view)
        except:
            pass
            
        rarity_text = f" ({self.rarity})" if self.rarity else ""
        if not self.rarity and not self.selected_ids: rarity_text = " SEMUA"
        
        await interaction.edit_original_response(content=f"✅ Berhasil men-salvage **{self.count}** ikan{rarity_text} menjadi **{self.total_scrap}x Scrap Metal** 🔩!", view=None)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Salvage dibatalkan.", view=None)


class FishingSalvageView(discord.ui.View):
    def __init__(self, cog, interaction, all_rows):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = interaction
        self.all_rows = all_rows
        self.page = 0
        self.items_per_page = 24
        self.max_pages = (len(all_rows) - 1) // self.items_per_page + 1
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_rows = self.all_rows[start:end]
        
        options = []
        for i, (fid, name, rarity, weight, price) in enumerate(current_rows, start=1):
            visual_id = i 
            options.append(discord.SelectOption(
                label=f"{visual_id}. {name} ({weight}kg)",
                description=f"Rarity: {rarity} | Price: {price}",
                value=str(fid),
                emoji="♻️"
            ))
            
        # Removed Select All from individual select to avoid clutter

            
        if options:
            select = discord.ui.Select(
                placeholder=f"Pilih ikan untuk di-salvage (Halaman {self.page + 1}/{self.max_pages})...",
                min_values=1,
                max_values=len(options),
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)
            
        # 2. Bulk Action Select Menu
        bulk_options = [
            discord.SelectOption(label="♻️ Salvage SEMUA (Salvage All)", value="salvage_all", description="Hancurkan semua ikan di inventory.", emoji="⚠️"),
            discord.SelectOption(label="⚪ Salvage Common", value="salvage_Common", description="Hancurkan semua ikan Common.", emoji="🔩"),
            discord.SelectOption(label="🟢 Salvage Uncommon", value="salvage_Uncommon", description="Hancurkan semua ikan Uncommon.", emoji="🔩"),
            discord.SelectOption(label="🔵 Salvage Rare", value="salvage_Rare", description="Hancurkan semua ikan Rare.", emoji="🔩"),
            discord.SelectOption(label="🟣 Salvage Epic", value="salvage_Epic", description="Hancurkan semua ikan Epic.", emoji="🔩"),
            discord.SelectOption(label="🟡 Salvage Legendary", value="salvage_Legendary", description="Hancurkan semua ikan Legendary.", emoji="🔩"),
        ]
        
        bulk_select = discord.ui.Select(
            placeholder="Opsi Salvage Rarity ...",
            min_values=1,
            max_values=1,
            options=bulk_options,
            row=1
        )
        bulk_select.callback = self.bulk_action_callback
        self.add_item(bulk_select)
        
        # Navigation
        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.page == 0))
            prev_btn.callback = self.prev_callback
            self.add_item(prev_btn)
            
            next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.page >= self.max_pages - 1))
            next_btn.callback = self.next_callback
            self.add_item(next_btn)

    async def send_initial_message(self):
        embed = self.build_embed()
        await self.original_interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    def build_embed(self):
        embed = discord.Embed(title=f"♻️ Salvage Ikan (Scrap Metal)", color=discord.Color.orange())
        embed.description = "Pilih ikan yang ingin dihancurkan menjadi **Scrap Metal**.\n*Ikan yang di-salvage akan hilang permanen!*"
        embed.set_footer(text=f"Total Ikan: {len(self.all_rows)} | Halaman {self.page + 1}/{self.max_pages}")
        return embed

    async def prev_callback(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            self.update_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def next_callback(self, interaction: discord.Interaction):
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_components()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        selected_ids = interaction.data["values"]
        
        conn = self.cog.get_conn()
        if not conn:
             await interaction.response.send_message("❌ Database Error", ephemeral=True)
             return
        
        # Handle Select All
        if "select_all" in selected_ids:
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            current_rows = self.all_rows[start:end]
            selected_ids = [str(row[0]) for row in current_rows]
            
            # Calculate potential scrap
            temp_scrap = 0
            for _ in selected_ids:
                temp_scrap += random.randint(1, 3) # Estimate (or pre-roll)
                
            # Show Confirmation
            confirm_view = ConfirmSalvageView(self, selected_ids, temp_scrap, len(selected_ids))
            await interaction.response.send_message(
                f"⚠️ **PERINGATAN!**\nKamu akan menghancurkan **{len(selected_ids)}** ikan di halaman ini menjadi estimasi **{temp_scrap}x Scrap Metal**.\nIkan yang sudah di-salvage **TIDAK BISA** dikembalikan!",
                view=confirm_view,
                ephemeral=True
            )
            if conn.is_connected(): conn.close()
            return

        total_scrap = 0
        deleted_count = 0
        
        try:
            cursor = conn.cursor()
            
            for fid in selected_ids:
                # Get fish details to verify ownership (paranoid check)
                cursor.execute('SELECT id FROM fish_inventory WHERE id = %s AND user_id = %s', (fid, self.original_interaction.user.id))
                if cursor.fetchone():
                    # Delete fish
                    cursor.execute('DELETE FROM fish_inventory WHERE id = %s', (fid,))
                    
                    # Calculate Scrap (Random 1-3)
                    scrap = random.randint(1, 3)
                    total_scrap += scrap
                    deleted_count += 1
            
            conn.commit()
            self.cog.add_material(self.original_interaction.user.id, "Scrap Metal", total_scrap)
            
            await interaction.response.send_message(f"✅ Berhasil men-salvage **{deleted_count}** ikan menjadi **{total_scrap}x Scrap Metal** 🔩!", ephemeral=True)
            
            # Refresh data
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = %s ORDER BY id DESC', (self.original_interaction.user.id,))
            self.all_rows = cursor.fetchall()
        finally:
             if conn.is_connected():
                cursor.close()
                conn.close()

        self.max_pages = (len(self.all_rows) - 1) // self.items_per_page + 1
        if self.page >= self.max_pages: self.page = max(0, self.max_pages - 1)
        
        self.update_components()
        # Edit original message to reflect changes
        try:
            await self.original_interaction.edit_original_response(embed=self.build_embed(), view=self)
        except:
            pass

    async def bulk_action_callback(self, interaction: discord.Interaction):
        action = interaction.data["values"][0]
        
        if action == "salvage_all":
            await self.salvage_all_callback(interaction)
            return
            
        if action.startswith("salvage_"):
            rarity = action.split("_")[1]
            
            # Calculate total scrap for this rarity
            total_scrap = 0
            count = 0
            for row in self.all_rows:
                if row[2] == rarity:
                    r_scrap = 1
                    if rarity == "Uncommon": r_scrap = 2
                    elif rarity == "Rare": r_scrap = 5
                    elif rarity == "Epic": r_scrap = 10
                    elif rarity == "Legendary": r_scrap = 20
                    total_scrap += r_scrap
                    count += 1
            
            if count == 0:
                await interaction.response.send_message(f"❌ Tidak ada ikan **{rarity}** di inventory!", ephemeral=True)
                return
                
            confirm_view = ConfirmSalvageView(self, [], total_scrap, count, rarity)
            await interaction.response.send_message(f"⚠️ Yakin ingin men-salvage **SEMUA {rarity}** ({count} ikan) menjadi **{total_scrap}x Scrap Metal**?", view=confirm_view, ephemeral=True)

    async def salvage_all_callback(self, interaction: discord.Interaction):
        total_scrap = 0
        count = len(self.all_rows)
        
        for row in self.all_rows:
            rarity = row[2]
            scrap = 1
            if rarity == "Uncommon": scrap = 2
            elif rarity == "Rare": scrap = 5
            elif rarity == "Epic": scrap = 10
            elif rarity == "Legendary": scrap = 20
            total_scrap += scrap
            
        if count == 0:
            await interaction.response.send_message("❌ Inventory kamu kosong!", ephemeral=True)
            return
            
        # Confirm Dialog
        confirm_view = ConfirmSalvageView(self, [], total_scrap, count)
        await interaction.response.send_message(f"⚠️ Yakin ingin men-salvage **SEMUA** ({count} ikan) menjadi **{total_scrap}x Scrap Metal**?", view=confirm_view, ephemeral=True)




class QuestClaimView(discord.ui.View):
    def __init__(self, cog, user_id, quests):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
        
        # Limit buttons to 5 per row, max 25. 
        # We have 3 daily + 2 weekly = 5 buttons max usually.
        for i, row in enumerate(quests, 1):
            # Handle variable unpacking safely (some rows might have extra cols if query changed)
            # Query: id, quest_type, target_criteria, target_value, progress, reward_amount, is_claimed, quest_period
            q_id = row[0]
            target = row[3]
            progress = row[4]
            is_claimed = row[6]
            
            disabled = True
            label = f"Claim Q{i}"
            style = discord.ButtonStyle.secondary
            
            if not is_claimed and progress >= target:
                disabled = False
                style = discord.ButtonStyle.success
                label = f"💰 Claim Q{i}"
            elif is_claimed:
                label = f"✅ Done Q{i}"
            
            button = discord.ui.Button(label=label, style=style, disabled=disabled, custom_id=f"claim_q_{q_id}")
            button.callback = self.create_callback(q_id)
            self.add_item(button)

    def create_callback(self, quest_id):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Ini bukan quest kamu!", ephemeral=True)
                return
            await self.cog.claim_quest_reward(interaction, quest_id)
        return callback


async def setup(bot):
    await bot.add_cog(Fishing(bot))
