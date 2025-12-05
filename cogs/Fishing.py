import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import random
import aiohttp
from datetime import datetime, timedelta

DB_PATH = 'database.db'

class Fishing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect(DB_PATH)
        self._init_db()
        
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
            {"name": "Mekong Giant Catfish", "base_price": 2000, "min_weight": 50.0, "max_weight": 300.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380001485689003/Mekong_Giant_Catfish.png?ex=69302286&is=692ed106&hm=359ccd5f2260a00f641dd5cdc53fe9ffc6f704fe349eaf4dea3848fb4cd3eb38&=&format=webp&quality=lossless"},
            {"name": "Arapaima Gigas", "base_price": 2500, "min_weight": 40.0, "max_weight": 200.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380240296902757/Arapaima_Gigas.png?ex=693022bf&is=692ed13f&hm=5a5de57bed01ee90e85a3127919f26c081c1c1694a8b2ac1a41c2e176b83d221&=&format=webp&quality=lossless"},
            {"name": "Blue Marlin", "base_price": 6500, "min_weight": 80.0, "max_weight": 300.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380445851226248/Blue_Marlin.png?ex=693022f0&is=692ed170&hm=aa1f4ca83e124fa62bd2e585f184d45b89561c9d34a0b4d824adc66ae93eb44c&=&format=webp&quality=lossless"},
            {"name": "Mola Mola", "base_price": 1500, "min_weight": 200.0, "max_weight": 1000.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380656367403100/Mola_Mola.png?ex=69302322&is=692ed1a2&hm=5123ec5a8a53d97dffcce7711c74d9ad6f59eb888776b820af5d72fcc4ec6a0e&=&format=webp&quality=lossless"},
            {"name": "Napoleon", "base_price": 8500, "min_weight": 5.0, "max_weight": 25.0, "spawn_weight": 3, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445380883803668551/ikan_Napoleon.png?ex=69302358&is=692ed1d8&hm=f3e400c46a8e6649d47b6cb188a87bf0a17df93db11a8431176e3c8d5903e512&=&format=webp&quality=lossless"},
            {"name": "Oarfish", "base_price": 8500, "min_weight": 20.0, "max_weight": 150.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381209411813396/Oarfish.png?ex=693023a6&is=692ed226&hm=cf155612ffba44e5c18a08af0c9684cd7972623baf439ca303ac2fea6c6418c6&=&format=webp&quality=lossless"},
            {"name": "Alligator Gar", "base_price": 2200, "min_weight": 10.0, "max_weight": 50.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381420200759498/Alligator_Gar.png?ex=693023d8&is=692ed258&hm=01d50aeedf38e8b599356993abec64b2540022fc84761bdd3120b091693b8173&=&format=webp&quality=lossless"},
            {"name": "Manta Ray", "base_price": 9500, "min_weight": 100.0, "max_weight": 500.0, "spawn_weight": 2, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381657325604975/Giant_Stingray.png?ex=69302410&is=692ed290&hm=9e678e8be34f391bd7f287f7c38b9f3d26dc640e6b54c49395aca657a2f473a4&=&format=webp&quality=lossless"},
            {"name": "Giant Stingray", "base_price": 9000, "min_weight": 50.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445381894790184991/Giant_Stingray.png?ex=69302449&is=692ed2c9&hm=e03c066f7ee0794cb4ce9f210c6ba04a0b71971eca7a5a21b37d8a6f2d0f9b0e&=&format=webp&quality=lossless"},
            {"name": "Hiu Martil", "base_price": 11000, "min_weight": 80.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382128668770324/Hiu_Martil.png?ex=69302481&is=692ed301&hm=d5b901ca9493960a0dffba7d282e089046d0e8edc2a366508b0758bc91611180&=&format=webp&quality=lossless"},
            {"name": "Hiu Macan", "base_price": 10000, "min_weight": 100.0, "max_weight": 500.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382414535884800/Hiu_Macan.png?ex=693024c5&is=692ed345&hm=71b89df8360057baca485c4090e0d5cb09bd5f0777657cfa8770423f0399c35f&=&format=webp&quality=lossless"},
            {"name": "Megalodon", "base_price": 15000, "min_weight": 8000.0, "max_weight": 30000.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445383272518651934/Megalodon.png?ex=69302592&is=692ed412&hm=bd3516d61f8352de5a84bf569adb7eeaaa586eb2d0653d635e87f055b517af49&=&format=webp&quality=lossless"},
            {"name": "Hiu Putih", "base_price": 12500, "min_weight": 100.0, "max_weight": 300.0, "spawn_weight": 1, "image_url": "https://media.discordapp.net/attachments/1080697175291469936/1445382645256294542/Great_White_Shark.png?ex=693024fc&is=692ed37c&hm=37fde9523241707a835e49b968fe72271807746ced52f20b1cc1658944a82d89&=&format=webp&quality=lossless"},
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
                    3: {"rate": 80, "cost": 2500, "scrap": 8, "pearl": 0, "risk": "downgrade"},
                    4: {"rate": 70, "cost": 5000, "scrap": 10, "pearl": 0, "risk": "downgrade"},
                    5: {"rate": 60, "cost": 10000, "scrap": 15, "pearl": 0, "risk": "reset"},
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
                    2: {"rate": 85, "cost": 5000, "scrap": 20, "pearl": 0, "risk": "downgrade"},
                    3: {"rate": 75, "cost": 10000, "scrap": 30, "pearl": 0, "risk": "downgrade"},
                    4: {"rate": 65, "cost": 20000, "scrap": 50, "pearl": 0, "risk": "reset"},
                    5: {"rate": 55, "cost": 40000, "scrap": 75, "pearl": 0, "risk": "reset"},
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
                    2: {"rate": 85, "cost": 10000, "scrap": 10, "pearl": 0, "risk": "downgrade"},
                    3: {"rate": 75, "cost": 20000, "scrap": 15, "pearl": 0, "risk": "downgrade"},
                    4: {"rate": 65, "cost": 35000, "scrap": 25, "pearl": 0, "risk": "reset"},
                    5: {"rate": 55, "cost": 50000, "scrap": 0, "pearl": 1, "risk": "reset"},
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
                    1: {"rate": 90, "cost": 10000, "scrap": 0, "pearl": 1, "risk": "downgrade"},
                    2: {"rate": 80, "cost": 25000, "scrap": 0, "pearl": 2, "risk": "downgrade"},
                    3: {"rate": 70, "cost": 50000, "scrap": 0, "pearl": 3, "risk": "reset"},
                    4: {"rate": 60, "cost": 75000, "scrap": 0, "pearl": 4, "risk": "reset"},
                    5: {"rate": 50, "cost": 100000, "scrap": 0, "pearl": 5, "risk": "reset"},
                    6: {"rate": 40, "cost": 200000, "scrap": 0, "pearl": 7, "risk": "reset"},
                    7: {"rate": 30, "cost": 350000, "scrap": 0, "pearl": 10, "risk": "reset"},
                    8: {"rate": 20, "cost": 500000, "scrap": 0, "pearl": 12, "risk": "reset"},
                    9: {"rate": 10, "cost": 750000, "scrap": 0, "pearl": 15, "risk": "destroy"},
                    10: {"rate": 3, "cost": 1000000, "scrap": 0, "pearl": 20, "risk": "destroy"}
                }
            }
        }

        self.conn.commit()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fish_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                fish_name TEXT,
                rarity TEXT,
                weight REAL,
                price INTEGER,
                caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_rods (
                user_id INTEGER,
                rod_name TEXT,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, rod_name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_profile (
                user_id INTEGER PRIMARY KEY,
                equipped_rod TEXT DEFAULT 'Common Rod',
                total_catches INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_materials (
                user_id INTEGER,
                material_name TEXT,
                amount INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, material_name)
            )
        ''')
        
        # Migration for existing tables
        try:
            cursor.execute("ALTER TABLE fishing_profile ADD COLUMN total_catches INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column likely exists

        try:
            cursor.execute("ALTER TABLE fishing_rods ADD COLUMN level INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column likely exists
            
        # Create fishing_quests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_quests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quest_type TEXT,
                target_criteria TEXT,
                target_value INTEGER,
                progress INTEGER DEFAULT 0,
                reward_amount INTEGER,
                is_claimed BOOLEAN DEFAULT 0,
                created_at DATE,
                quest_period TEXT DEFAULT 'daily',
                expiration_date TIMESTAMP,
                reward_type TEXT DEFAULT 'coin',
                reward_name TEXT
            )
        ''')
        
        self.conn.commit()
        
        # Migration for Quests (Add new columns)
        # Migration for Quests (Add new columns)
        try:
            cursor.execute("ALTER TABLE fishing_quests ADD COLUMN quest_period TEXT DEFAULT 'daily'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE fishing_quests ADD COLUMN expiration_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE fishing_quests ADD COLUMN reward_type TEXT DEFAULT 'coin'")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE fishing_quests ADD COLUMN reward_name TEXT")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def generate_quests(self, user_id):
        """Generate Daily and Weekly quests with variations"""
        cursor = self.conn.cursor()
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        # --- DAILY QUESTS (5 per day) ---
        cursor.execute('SELECT id FROM fishing_quests WHERE user_id = ? AND quest_period = ? AND created_at = ?', (user_id, 'daily', today_str))
        if not cursor.fetchone():
            daily_templates = [
                {"type": "catch_any", "criteria": "any", "min": 10, "max": 20, "reward_mult": 20},
                {"type": "catch_rarity", "criteria": "Common", "min": 10, "max": 15, "reward_mult": 30},
                {"type": "catch_rarity", "criteria": "Uncommon", "min": 5, "max": 10, "reward_mult": 50},
                {"type": "catch_rarity", "criteria": "Rare", "min": 2, "max": 5, "reward_mult": 100},
                {"type": "catch_weight", "criteria": "2", "min": 5, "max": 10, "reward_mult": 40}, # > 2kg
                {"type": "catch_weight", "criteria": "5", "min": 2, "max": 5, "reward_mult": 80}, # > 5kg
                {"type": "catch_weight", "criteria": "1", "min": 10, "max": 15, "reward_mult": 30}, # > 1kg (Actually logic says >= criteria, so this works)
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
            expiry_daily = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 'daily', ?)
                ''', (user_id, quest["type"], quest["criteria"], target_val, reward_amount, reward_type, reward_name, today_str, expiry_daily))

        # --- WEEKLY QUESTS (3 per week, reset Friday) ---
        # Calculate start of week (Friday)
        # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # If today is Fri (4), offset is 0. If Sat (5), offset 1. If Thu (3), offset 6 (last Fri).
        # (now.weekday() - 4) % 7 gives days since last Friday.
        days_since_friday = (now.weekday() - 4) % 7
        start_of_week = (now - timedelta(days=days_since_friday)).strftime('%Y-%m-%d')
        
        cursor.execute('SELECT id FROM fishing_quests WHERE user_id = ? AND quest_period = ? AND created_at = ?', (user_id, 'weekly', start_of_week))
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
                {"type": "catch_weight", "criteria": "100", "min": 1, "max": 2, "reward_mult": 2000}, # > 100kg (Hard)
                {"type": "total_weight", "criteria": "total", "min": 600, "max": 800, "reward_mult": 25}, # Extreme Grind
            ]
            
            selected_weekly = random.sample(weekly_templates, 3)
            # Expiry: Next Friday
            expiry_weekly = (now + timedelta(days=(7 - days_since_friday))).replace(hour=0, minute=0, second=0, microsecond=0)
            
            for quest in selected_weekly:
                target_val = random.randint(quest["min"], quest["max"])
                
                # Reward Logic (60% Coin, 40% Magic Pearl)
                reward_type = 'coin'
                reward_name = None
                reward_amount = 0
                
                if random.random() < 0.40:
                    reward_type = 'material'
                    reward_name = 'Magic Pearl'
                    reward_amount = random.randint(1, 3)
                else:
                    base_reward = target_val * quest["reward_mult"]
                    reward_amount = min(base_reward + random.randint(1000, 3000), 15000) # Max 15k
                
                cursor.execute('''
                    INSERT INTO fishing_quests (user_id, quest_type, target_criteria, target_value, reward_amount, reward_type, reward_name, is_claimed, created_at, quest_period, expiration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 'weekly', ?)
                ''', (user_id, quest["type"], quest["criteria"], target_val, reward_amount, reward_type, reward_name, start_of_week, expiry_weekly))
        
        self.conn.commit()

    def get_material(self, user_id, material_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT amount FROM fishing_materials WHERE user_id = ? AND material_name = ?', (user_id, material_name))
        res = cursor.fetchone()
        return res[0] if res else 0

    def add_material(self, user_id, material_name, amount):
        cursor = self.conn.cursor()
        current = self.get_material(user_id, material_name)
        new_amount = current + amount
        if new_amount < 0: new_amount = 0
        
        cursor.execute('''
            INSERT INTO fishing_materials (user_id, material_name, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, material_name) DO UPDATE SET amount = ?
        ''', (user_id, material_name, new_amount, new_amount))
        self.conn.commit()
        return new_amount

    def get_rod_level(self, user_id, rod_name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT level FROM fishing_rods WHERE user_id = ? AND rod_name = ?', (user_id, rod_name))
        res = cursor.fetchone()
        return res[0] if res else 0

    def update_rod_level(self, user_id, rod_name, new_level):
        cursor = self.conn.cursor()
        if new_level < 0: new_level = 0
        
        # Check if rod exists, if not (e.g. Common Rod default), insert it
        cursor.execute('INSERT OR IGNORE INTO fishing_rods (user_id, rod_name, level) VALUES (?, ?, ?)', (user_id, rod_name, 0))
        
        cursor.execute('UPDATE fishing_rods SET level = ? WHERE user_id = ? AND rod_name = ?', (new_level, user_id, rod_name))
        self.conn.commit()

    async def check_quest_progress(self, interaction, fish_name, rarity, weight):
        """Check and update quest progress (Daily & Weekly)"""
        user_id = interaction.user.id
        now = datetime.now()
        cursor = self.conn.cursor()
        
        # Check active quests (not claimed, not expired)
        cursor.execute('''
            SELECT id, quest_type, target_criteria, target_value, progress 
            FROM fishing_quests 
            WHERE user_id = ? AND is_claimed = 0 AND (expiration_date IS NULL OR expiration_date > ?)
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
                increment = int(weight) # Or float if DB supports it, but progress is INT. Let's round or accumulate scaled.
                # Since progress is INT, let's just add weight as INT for simplicity or change schema to REAL. 
                # Schema is INTEGER. Let's round weight to nearest int or just int(weight).
                # Better: int(weight * 10) to keep 1 decimal precision if needed, but for now int(weight) is fine for "Total 50kg".
                # Actually, if catch is 0.5kg, int is 0. Let's use ceil or accumulate 1 for any catch? No.
                # Let's assume target is in KG. If we want precision, we need REAL.
                # For now, let's just add weight.
                increment = max(1, int(weight)) 
            
            if increment > 0:
                new_progress = progress + increment
                cursor.execute('UPDATE fishing_quests SET progress = ? WHERE id = ?', (new_progress, q_id))
                
                if new_progress >= target:
                    completed_quests.append(q_id)
        
        self.conn.commit()
        
        if completed_quests:
            try:
                await interaction.followup.send("🎉 **Quest Selesai!** Cek `/fish quests` untuk klaim hadiah.", ephemeral=True)
            except:
                pass

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
        cursor = self.conn.cursor()
        cursor.execute('SELECT equipped_rod FROM fishing_profile WHERE user_id = ?', (user_id,))
        res = cursor.fetchone()
        return res[0] if res else "Common Rod"

    def get_owned_rods(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT rod_name FROM fishing_rods WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        owned = [r[0] for r in rows]
        if "Common Rod" not in owned:
            owned.append("Common Rod")
        return owned

    def get_weight_leaderboard(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, fish_name, weight, rarity 
            FROM fish_inventory 
            ORDER BY weight DESC 
            LIMIT 15
        ''')
        return cursor.fetchall()

    def get_networth_leaderboard(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, SUM(price) as total_value 
            FROM fish_inventory 
            GROUP BY user_id 
            ORDER BY total_value DESC 
            LIMIT 15
        ''')
        return cursor.fetchall()

    def get_top_fisher_leaderboard(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, total_catches 
            FROM fishing_profile 
            ORDER BY total_catches DESC 
            LIMIT 15
        ''')
        return cursor.fetchall()
    # Define Group for /fish commands
    fish_group = app_commands.Group(name="fish", description="Fishing commands")

    @fish_group.command(name="catch", description="Memancing ikan (Cooldown: 15s)")
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: (i.guild_id, i.user.id))
    async def catch(self, interaction: discord.Interaction):
        # Get Equipped Rod Stats
        equipped_rod = self.get_equipped_rod(interaction.user.id)
        rod_level = self.get_rod_level(interaction.user.id, equipped_rod)
        rod_stats = self.rod_data.get(equipped_rod, self.rod_data["Common Rod"])
        
        # Calculate Total Boosts
        base_weight_boost = rod_stats["weight_boost"]
        base_rarity_boost = rod_stats["rarity_boost"]
        scaling_weight = rod_stats.get("scaling_weight", 0.1)
        scaling_rarity = rod_stats.get("scaling_rarity", 1)
        
        weight_boost = base_weight_boost + (rod_level * scaling_weight)
        rarity_boost = base_rarity_boost + (rod_level * scaling_rarity)
        
        # 1. Rarity Roll (Apply Boost)
        rarities = list(self.rarity_weights.keys())
        rarity_weights = list(self.rarity_weights.values())
        
        # Boost logic: Increase weight of higher rarities based on rod
        if rarity_boost > 0:
            rarity_weights[2] += rarity_boost # Rare
            rarity_weights[3] += rarity_boost # Epic
            rarity_weights[4] += rarity_boost # Legendary
            
        rarity = random.choices(rarities, weights=rarity_weights, k=1)[0]
        
        # 2. Fish Roll (Weighted by spawn_weight)
        fish_list = self.fish_data[rarity]
        fish_weights = [f["spawn_weight"] for f in fish_list]
        fish_info = random.choices(fish_list, weights=fish_weights, k=1)[0]
        
        name = fish_info["name"]
        image_url = fish_info.get("image_url")
        base_price = fish_info["base_price"]
        min_w = fish_info["min_weight"]
        max_w = fish_info["max_weight"]
        
        # 3. Weight Roll (Random between min and max) * Boost
        raw_weight = random.uniform(min_w, max_w)
        weight = round(raw_weight * weight_boost, 2)
        
        # 4. Final Price Calculation
        # Price increases linearly with weight: Min Weight = Base Price
        weight_multiplier = weight / min_w
        final_price = int(base_price * weight_multiplier)
        
        # Save to DB
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO fish_inventory (user_id, fish_name, rarity, weight, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (interaction.user.id, name, rarity, weight, final_price))
        
        # Increment total_catches
        cursor.execute('''
            INSERT INTO fishing_profile (user_id, total_catches) 
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET total_catches = total_catches + 1
        ''', (interaction.user.id,))
        
        self.conn.commit()
        
        # Material Drop Chance
        material_msg = ""
        # 10% chance for Scrap Metal
        if random.random() < 0.10:
            scrap_amount = random.randint(1, 3)
            self.add_material(interaction.user.id, "Scrap Metal", scrap_amount)
            material_msg = f"\n🔩 Kamu menemukan **{scrap_amount}x Scrap Metal**!"
            
        # 1% chance for Magic Pearl (only if Rare+)
        if rarity in ["Rare", "Epic", "Legendary"] and random.random() < 0.01:
            self.add_material(interaction.user.id, "Magic Pearl", 1)
            material_msg += f"\n🔮 WOW! Kamu menemukan **1x Magic Pearl**!"

        # Embed
        color_map = {
            "Common": discord.Color.light_grey(),
            "Uncommon": discord.Color.green(),
            "Rare": discord.Color.blue(),
            "Epic": discord.Color.purple(),
            "Legendary": discord.Color.gold()
        }
        
        embed = discord.Embed(
            title="🎣 Hasil Pancingan",
            description=f"Kamu mendapatkan **{name}**!{material_msg}",
            color=color_map.get(rarity, discord.Color.default())
        )
        embed.add_field(name="Rarity", value=rarity, inline=True)
        embed.add_field(name="Berat", value=f"{weight} kg", inline=True)
        embed.add_field(name="Harga", value=f"💰 {final_price}", inline=True)
        
        if image_url:
            embed.set_image(url=image_url)
        
        footer_text = ""
        if equipped_rod != "Common Rod" or rod_level > 0:
            footer_text = f"Rod: {equipped_rod} +{rod_level} | Bonus: +{int((weight_boost-1)*100)}% Weight"
        
        if footer_text:
            embed.set_footer(text=footer_text)
            
        self.generate_quests(interaction.user.id) # Ensure quests exist
        await self.check_quest_progress(interaction, name, rarity, weight)
        
        await interaction.response.send_message(embed=embed)

    @catch.error
    async def catch_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"⏳ Tunggu **{error.retry_after:.1f}s** lagi sebelum memancing!", ephemeral=True)
                else:
                    await interaction.followup.send(f"⏳ Tunggu **{error.retry_after:.1f}s** lagi sebelum memancing!", ephemeral=True)
            except Exception:
                pass

    @fish_group.command(name="inventory", description="Lihat hasil pancinganmu")
    async def inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (interaction.user.id,))
        rows = cursor.fetchall()
        
        if not rows:
            await interaction.followup.send("🎒 Tas ikanmu kosong! Ayo memancing dulu.", ephemeral=True)
            return
            
        view = FishingInventoryView(self, interaction, rows)
        await view.send_initial_message()
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

        view = FishTradeView(self, interaction.user, user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @fish_group.command(name="quests", description="Lihat misi harian & mingguan fishing")
    async def fish_quests(self, interaction: discord.Interaction):
        self.generate_quests(interaction.user.id)
        
        cursor = self.conn.cursor()
        now = datetime.now()
        
        # Fetch Active Quests
        cursor.execute('''
            SELECT id, quest_type, target_criteria, target_value, progress, reward_amount, is_claimed, quest_period, reward_type, reward_name 
            FROM fishing_quests 
            WHERE user_id = ? AND (expiration_date IS NULL OR expiration_date > ?)
            ORDER BY quest_period, is_claimed, id
        ''', (interaction.user.id, now))
        quests = cursor.fetchall()
        
        if not quests:
            await interaction.response.send_message("❌ Gagal memuat quest. Coba lagi nanti.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📜 Fishing Quests",
            description=f"Selesaikan misi untuk mendapatkan hadiah menarik!",
            color=discord.Color.gold()
        )
        
        view = QuestClaimView(self, interaction.user.id, quests)
        
        daily_text = ""
        weekly_text = ""
        
        for i, (q_id, q_type, criteria, target, progress, reward, is_claimed, period, r_type, r_name) in enumerate(quests, 1):
            # Format Quest Description
            desc = ""
            if q_type == "catch_any":
                desc = f"Tangkap {target} ikan apa saja"
            elif q_type == "catch_rarity":
                desc = f"Tangkap {target} ikan {criteria}"
            elif q_type == "catch_weight":
                desc = f"Tangkap {target} ikan > {criteria}kg"
            elif q_type == "catch_specific":
                desc = f"Tangkap {target} {criteria}"
            elif q_type == "total_weight":
                desc = f"Total tangkapan {target}kg"
            
            # Progress Bar
            percent = min(progress / target, 1.0)
            bar_len = 8
            filled = int(percent * bar_len)
            bar = "▓" * filled + "░" * (bar_len - filled)
            
            status = ""
            if is_claimed:
                status = "✅"
            elif progress >= target:
                status = "🎁 **SIAP KLAIM**"
            else:
                status = f"{int(percent*100)}%"
            
            # Reward Display
            reward_str = ""
            if r_type == 'material':
                icon = "🔩" if "Scrap" in r_name else "🔮"
                reward_str = f"{icon} **{reward}x {r_name}**"
            else:
                reward_str = f"💰 **{reward}**"
            
            entry = f"`{desc}`\n{bar} ({progress}/{target}) | {reward_str} {status}\n"
            
            if period == 'weekly':
                weekly_text += entry
            else:
                daily_text += entry
                
        if daily_text:
            embed.add_field(name="# 📅 Daily Quests", value=daily_text, inline=False)
        else:
            embed.add_field(name="# 📅 Daily Quests", value="*Tidak ada quest aktif.*", inline=False)
            
        if weekly_text:
            embed.add_field(name="# 📅 Weekly Quests", value=weekly_text, inline=False)
        else:
            embed.add_field(name="# 📅 Weekly Quests", value="*Tidak ada quest aktif.*", inline=False)
            
        await interaction.response.send_message(embed=embed, view=view)

    async def claim_quest_reward(self, interaction: discord.Interaction, quest_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT reward_amount, is_claimed, progress, target_value, reward_type, reward_name FROM fishing_quests WHERE id = ?', (quest_id,))
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
        cursor.execute('UPDATE fishing_quests SET is_claimed = 1 WHERE id = ?', (quest_id,))
        self.conn.commit()
        
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
            
        # Refresh UI (Optional, user can re-run command)



    @fish_group.command(name="catalog", description="Show fishing catalog (Fish List)")
    async def catalog(self, interaction: discord.Interaction):
        payload = self.build_catalog_payload("Common")
        await self.send_raw_payload(interaction, payload)

    @fish_group.command(name="salvage", description="Salvage fish into materials (Scrap Metal)")
    async def salvage(self, interaction: discord.Interaction):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (interaction.user.id,))
        rows = cursor.fetchall()
        
        if not rows:
            await interaction.response.send_message("🎒 Tas ikanmu kosong! Tidak ada yang bisa di-salvage.", ephemeral=True)
            return
            
        view = FishingSalvageView(self, interaction, rows)
        await view.send_initial_message()

    @fish_group.command(name="forge", description="Upgrade your fishing rod (Tempa)")
    async def forge(self, interaction: discord.Interaction):
        owned_rods = self.get_owned_rods(interaction.user.id)
        view = FishingForgeView(self, interaction, owned_rods)
        await view.send_initial_message()



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
        self.conn.close()

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
        
        # Add Sell All Option
        options.append(discord.SelectOption(
            label="💰 Jual SEMUA Ikan (Sell All)",
            description="Menjual semua ikan di inventory ini.",
            value="sell_all",
            emoji="⚠️"
        ))
        
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
        
        # 2. Navigation Buttons
        prev_btn = discord.ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, disabled=(self.page == 0))
        prev_btn.callback = self.prev_callback
        self.add_item(prev_btn)
        
        next_btn = discord.ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, disabled=(self.page >= self.max_pages - 1))
        next_btn.callback = self.next_callback
        self.add_item(next_btn)

    async def send_initial_message(self):
        embed = self.build_embed()
        await self.original_interaction.followup.send(embed=embed, view=self)

    def build_embed(self):
        total_value = sum(row[4] for row in self.all_rows)
        
        embed = discord.Embed(title=f"🎒 Tas Ikan {self.original_interaction.user.display_name}", color=discord.Color.blue())
        embed.set_footer(text=f"Total Nilai: {total_value:,} koin | Halaman {self.page + 1}/{self.max_pages}")
        
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
        
        # Check for Sell All
        if "sell_all" in selected_ids:
            await self.sell_all_callback(interaction)
            return
        
        cursor = self.cog.conn.cursor()
        
        total_price = 0
        count = 0
        
        for fid in selected_ids:
            cursor.execute('SELECT price FROM fish_inventory WHERE id = ?', (fid,))
            res = cursor.fetchone()
            if res:
                total_price += res[0]
                cursor.execute('DELETE FROM fish_inventory WHERE id = ?', (fid,))
                count += 1
                
        self.cog.conn.commit()
        economy = self.cog.get_economy()
        if economy:
            economy.update_balance(interaction.user.id, total_price)
            
        await interaction.response.send_message(f"💰 Berhasil menjual **{count}** ikan seharga **{total_price:,}** koin!", ephemeral=True)
        
        # Refresh data and view
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (self.original_interaction.user.id,))
        self.all_rows = cursor.fetchall()
        self.max_pages = (len(self.all_rows) - 1) // self.items_per_page + 1
        
        if self.page >= self.max_pages and self.page > 0:
            self.page = self.max_pages - 1
            
        self.update_components()
        await interaction.message.edit(embed=self.build_embed(), view=self)

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
    def __init__(self, inventory_view, total_price, count):
        super().__init__(timeout=60)
        self.inventory_view = inventory_view
        self.total_price = total_price
        self.count = count
        
    @discord.ui.button(label="✅ YA, JUAL SEMUA", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Update Economy
        economy = self.inventory_view.cog.get_economy()
        if economy:
            economy.update_balance(interaction.user.id, self.total_price)
            
        # Delete All Fish
        cursor = self.inventory_view.cog.conn.cursor()
        cursor.execute('DELETE FROM fish_inventory WHERE user_id = ?', (interaction.user.id,))
        self.inventory_view.cog.conn.commit()
        
        # Update Inventory View
        self.inventory_view.all_rows = []
        self.inventory_view.page = 0
        self.inventory_view.max_pages = 1
        self.inventory_view.update_components()
        
        await self.inventory_view.original_interaction.edit_original_response(embed=self.inventory_view.build_embed(), view=self.inventory_view)
        await interaction.response.edit_message(content=f"✅ Berhasil menjual **{self.count}** ikan seharga **{self.total_price:,}** koin!", view=None)

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
        cursor = self.cog.conn.cursor()
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (user.id,))
        rows = cursor.fetchall()
        
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
        cursor = self.cog.conn.cursor()
        
        # Swap Owner
        for item in self.initiator_offer:
            cursor.execute('UPDATE fish_inventory SET user_id = ? WHERE id = ?', (self.target.id, item['id']))
            
        for item in self.target_offer:
            cursor.execute('UPDATE fish_inventory SET user_id = ? WHERE id = ?', (self.initiator.id, item['id']))
            
        self.cog.conn.commit()
        
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
        cursor = self.trade_view.cog.conn.cursor()
        new_items = []
        for fid in selected_ids:
            cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE id = ?', (fid,))
            row = cursor.fetchone()
            if row:
                item = {"id": row[0], "name": row[1], "rarity": row[2], "weight": row[3], "price": row[4]}
                new_items.append(item)
        
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
    def __init__(self, cog, user):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        owned_rods = self.cog.get_owned_rods(self.user.id)
        
        options = []
        for rod_name, stats in self.cog.rod_data.items():
            if rod_name == "Common Rod": continue # Cannot buy default
            
            price = stats["price"]
            emoji = stats["emoji"]
            is_owned = rod_name in owned_rods
            
            label = f"{rod_name} - 💰{price:,}" if not is_owned else f"{rod_name} (Owned)"
            desc = f"Weight x{stats['weight_boost']} | Rarity +{stats['rarity_boost']}%"
            
            options.append(discord.SelectOption(
                label=label,
                description=desc,
                value=rod_name,
                emoji=emoji,
                default=False
            ))
            
        # Add Lucky Charm
        options.append(discord.SelectOption(
            label="Lucky Charm - 💰100,000",
            description="Increase forge success rate significantly!",
            value="Lucky Charm",
            emoji="🍀",
            default=False
        ))
            
        select = discord.ui.Select(placeholder="Buy a fishing rod or item...", options=options)
        select.callback = self.callback
        self.add_item(select)

    def build_embed(self):
        embed = discord.Embed(title="🎣 Fishing Shop", color=discord.Color.gold())
        embed.description = "Upgrade your rod to catch bigger and rarer fish!"
        
        owned_rods = self.cog.get_owned_rods(self.user.id)
        equipped = self.cog.get_equipped_rod(self.user.id)
        
        for rod_name, stats in self.cog.rod_data.items():
            status = "✅ Owned" if rod_name in owned_rods else f"💰 {stats['price']:,}"
            if rod_name == equipped: status += " (Equipped)"
            
            embed.add_field(
                name=f"{stats['emoji']} {rod_name}",
                value=f"**Price:** {status}\n**Stats:** Weight x{stats['weight_boost']} | Rarity +{stats['rarity_boost']}%",
                inline=False
            )
            
        # Add Lucky Charm Info
        user_charm = self.cog.get_material(self.user.id, "Lucky Charm")
        embed.add_field(
            name="🍀 Lucky Charm",
            value=f"**Price:** 💰 100,000\n**Effect:** +50% Forge Success Rate\n**Owned:** {user_charm}",
            inline=False
        )
        return embed

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This shop is not for you!", ephemeral=True)
            return
            
        rod_name = interaction.data["values"][0]
        
        # Handle Lucky Charm Purchase
        if rod_name == "Lucky Charm":
            price = 100000
            economy = self.cog.get_economy()
            if not economy:
                await interaction.response.send_message("❌ Economy system error.", ephemeral=True)
                return
                
            bal = economy.get_balance(self.user.id)
            if bal < price:
                await interaction.response.send_message(f"❌ Not enough money! You need **{price:,}** coins.", ephemeral=True)
                return
                
            economy.update_balance(self.user.id, -price)
            self.cog.add_material(self.user.id, "Lucky Charm", 1)
            
            await interaction.response.send_message(f"🎉 Successfully bought **1x Lucky Charm** 🍀!", ephemeral=True)
            self.update_components()
            await interaction.message.edit(embed=self.build_embed(), view=self)
            return

        price = self.cog.rod_data[rod_name]["price"]
        owned_rods = self.cog.get_owned_rods(self.user.id)
        
        if rod_name in owned_rods:
            await interaction.response.send_message("✅ You already own this rod!", ephemeral=True)
            return
            
        economy = self.cog.get_economy()
        if not economy:
            await interaction.response.send_message("❌ Economy system error.", ephemeral=True)
            return
            
        bal = economy.get_balance(self.user.id)
        if bal < price:
            await interaction.response.send_message(f"❌ Not enough money! You need **{price:,}** coins.", ephemeral=True)
            return
            
        # Buy logic
        economy.update_balance(self.user.id, -price)
        
        cursor = self.cog.conn.cursor()
        cursor.execute('INSERT INTO fishing_rods (user_id, rod_name) VALUES (?, ?)', (self.user.id, rod_name))
        self.cog.conn.commit()
        
        await interaction.response.send_message(f"🎉 Successfully bought **{rod_name}**!", ephemeral=True)
        
        self.update_components()
        await interaction.message.edit(embed=self.build_embed(), view=self)

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
        
        cursor = self.cog.conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO fishing_profile (user_id, equipped_rod) VALUES (?, ?)', (self.user.id, rod_name))
        self.cog.conn.commit()
        
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
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)



class FishingSalvageView(discord.ui.View):
    def __init__(self, cog, interaction, all_rows):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = interaction
        self.all_rows = all_rows
        self.page = 0
        self.items_per_page = 25
        self.max_pages = (len(all_rows) - 1) // self.items_per_page + 1
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_rows = self.all_rows[start:end]
        
        options = []
        
        # Add Salvage All Option
        options.append(discord.SelectOption(
            label="♻️ Salvage SEMUA Ikan (Dapat Scrap Metal)",
            description="Hancurkan semua ikan jadi material.",
            value="salvage_all",
            emoji="🔥"
        ))
        
        for i, (fid, name, rarity, weight, price) in enumerate(current_rows, start=1):
            visual_id = i 
            # Calculate scrap amount based on rarity
            scrap_amount = 1
            if rarity == "Uncommon": scrap_amount = 2
            elif rarity == "Rare": scrap_amount = 5
            elif rarity == "Epic": scrap_amount = 10
            elif rarity == "Legendary": scrap_amount = 20
            
            options.append(discord.SelectOption(
                label=f"{visual_id}. {name} ({rarity}) -> {scrap_amount} Scrap",
                description=f"Weight: {weight}kg",
                value=str(fid),
                emoji="🔩"
            ))
            
        select = discord.ui.Select(
            placeholder=f"Pilih ikan untuk di-salvage (Halaman {self.page + 1}/{self.max_pages})...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        # Navigation Buttons
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
        embed = discord.Embed(title="♻️ Salvage Station", description="Hancurkan ikan untuk mendapatkan **Scrap Metal** 🔩.", color=discord.Color.orange())
        embed.set_footer(text=f"Halaman {self.page + 1}/{self.max_pages}")
        
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_rows = self.all_rows[start:end]
        
        desc = ""
        for i, (fid, name, rarity, weight, price) in enumerate(current_rows, start=1):
            scrap = 1
            if rarity == "Uncommon": scrap = 2
            elif rarity == "Rare": scrap = 5
            elif rarity == "Epic": scrap = 10
            elif rarity == "Legendary": scrap = 20
            
            desc += f"`{i}.` **{name}** ({rarity}) ➡️ **{scrap} Scrap Metal**\n"
            
        embed.description = desc
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
        
        if "salvage_all" in selected_ids:
            await self.salvage_all_callback(interaction)
            return
        
        cursor = self.cog.conn.cursor()
        
        total_scrap = 0
        count = 0
        
        for fid in selected_ids:
            cursor.execute('SELECT rarity FROM fish_inventory WHERE id = ?', (fid,))
            res = cursor.fetchone()
            if res:
                rarity = res[0]
                scrap = 1
                if rarity == "Uncommon": scrap = 2
                elif rarity == "Rare": scrap = 5
                elif rarity == "Epic": scrap = 10
                elif rarity == "Legendary": scrap = 20
                
                total_scrap += scrap
                cursor.execute('DELETE FROM fish_inventory WHERE id = ?', (fid,))
                count += 1
                
        self.cog.conn.commit()
        self.cog.add_material(interaction.user.id, "Scrap Metal", total_scrap)
            
        await interaction.response.send_message(f"♻️ Berhasil salvage **{count}** ikan menjadi **{total_scrap} Scrap Metal** 🔩!", ephemeral=True)
        
        # Refresh
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (self.original_interaction.user.id,))
        self.all_rows = cursor.fetchall()
        self.max_pages = (len(self.all_rows) - 1) // self.items_per_page + 1
        
        if self.page >= self.max_pages and self.page > 0:
            self.page = self.max_pages - 1
            
        self.update_components()
        await interaction.message.edit(embed=self.build_embed(), view=self)

    async def salvage_all_callback(self, interaction: discord.Interaction):
        total_scrap = 0
        count = 0
        
        for row in self.all_rows:
            rarity = row[2]
            scrap = 1
            if rarity == "Uncommon": scrap = 2
            elif rarity == "Rare": scrap = 5
            elif rarity == "Epic": scrap = 10
            elif rarity == "Legendary": scrap = 20
            total_scrap += scrap
            count += 1
            
        # Confirm Dialog
        confirm_view = ConfirmSalvageAllView(self, total_scrap, count)
        await interaction.response.send_message(f"⚠️ Yakin ingin salvage **SEMUA** ({count} ikan) menjadi **{total_scrap} Scrap Metal**?", view=confirm_view, ephemeral=True)

class ConfirmSalvageAllView(discord.ui.View):
    def __init__(self, salvage_view, total_scrap, count):
        super().__init__(timeout=60)
        self.salvage_view = salvage_view
        self.total_scrap = total_scrap
        self.count = count
        
    @discord.ui.button(label="✅ YA, SALVAGE SEMUA", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Add Materials
        self.salvage_view.cog.add_material(interaction.user.id, "Scrap Metal", self.total_scrap)
            
        # Delete All Fish
        cursor = self.salvage_view.cog.conn.cursor()
        cursor.execute('DELETE FROM fish_inventory WHERE user_id = ?', (interaction.user.id,))
        self.salvage_view.cog.conn.commit()
        
        # Update View
        self.salvage_view.all_rows = []
        self.salvage_view.page = 0
        self.salvage_view.max_pages = 1
        self.salvage_view.update_components()
        
        await self.salvage_view.original_interaction.edit_original_response(embed=self.salvage_view.build_embed(), view=self.salvage_view)
        await interaction.response.edit_message(content=f"✅ Berhasil salvage **{self.count}** ikan menjadi **{self.total_scrap} Scrap Metal** 🔩!", view=None)

    @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Salvage dibatalkan.", view=None)

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
            emoji = self.cog.rod_data[rod_name]["emoji"]
            
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
        await self.original_interaction.response.send_message(embed=embed, view=self, ephemeral=True)

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
        user_id = interaction.user.id
        rod_name = self.selected_rod
        level = self.cog.get_rod_level(user_id, rod_name)
        next_level = level + 1
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
                cursor = self.cog.conn.cursor()
                cursor.execute('DELETE FROM fishing_rods WHERE user_id = ? AND rod_name = ?', (user_id, rod_name))
                
                # Check if equipped, if so, equip Common Rod
                equipped = self.cog.get_equipped_rod(user_id)
                if equipped == rod_name:
                    cursor.execute('UPDATE fishing_profile SET equipped_rod = ? WHERE user_id = ?', ("Common Rod", user_id))
                    
                self.cog.conn.commit()
                result_text = "💥 **GAGAL TOTAL!** Rod **HANCUR** berkeping-keping! 💀"
                self.selected_rod = None # Reset selection
                
            self.last_result = f"💀 **GAGAL!** {result_text}"
            self.last_status = "failure"
            
        # Refresh View
        self.update_components()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)



class ConfirmSalvageView(discord.ui.View):
    def __init__(self, salvage_view, selected_ids, total_scrap, count):
        super().__init__(timeout=60)
        self.salvage_view = salvage_view
        self.selected_ids = selected_ids
        self.total_scrap = total_scrap
        self.count = count
        
    @discord.ui.button(label="✅ YA, SALVAGE SEMUA", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        cursor = self.salvage_view.cog.conn.cursor()
        
        # Execute Deletion
        for fid in self.selected_ids:
             cursor.execute('DELETE FROM fish_inventory WHERE id = ?', (fid,))
             
        self.salvage_view.cog.conn.commit()
        self.salvage_view.cog.add_material(interaction.user.id, "Scrap Metal", self.total_scrap)
        
        # Update Parent View
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (self.salvage_view.original_interaction.user.id,))
        self.salvage_view.all_rows = cursor.fetchall()
        self.salvage_view.max_pages = (len(self.salvage_view.all_rows) - 1) // self.salvage_view.items_per_page + 1
        if self.salvage_view.page >= self.salvage_view.max_pages: self.salvage_view.page = max(0, self.salvage_view.max_pages - 1)
        
        self.salvage_view.update_components()
        
        try:
            await self.salvage_view.original_interaction.edit_original_response(embed=self.salvage_view.build_embed(), view=self.salvage_view)
        except:
            pass
            
        await interaction.response.edit_message(content=f"✅ Berhasil men-salvage **{self.count}** ikan menjadi **{self.total_scrap}x Scrap Metal** 🔩!", view=None)

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
            
        # Add Select All Option
        options.insert(0, discord.SelectOption(
            label="♻️ Salvage SEMUA di Halaman Ini",
            description="Hancurkan semua ikan di halaman ini menjadi Scrap Metal.",
            value="select_all",
            emoji="⚠️"
        ))
            
        if options:
            select = discord.ui.Select(
                placeholder=f"Pilih ikan untuk di-salvage (Halaman {self.page + 1}/{self.max_pages})...",
                min_values=1,
                max_values=len(options),
                options=options
            )
            select.callback = self.select_callback
            self.add_item(select)
        
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
        embed.set_footer(text=f"Halaman {self.page + 1}/{self.max_pages}")
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
        cursor = self.cog.conn.cursor()
        
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
            return

        total_scrap = 0
        deleted_count = 0
        
        for fid in selected_ids:
            # Get fish details to verify ownership (paranoid check)
            cursor.execute('SELECT id FROM fish_inventory WHERE id = ? AND user_id = ?', (fid, self.original_interaction.user.id))
            if cursor.fetchone():
                # Delete fish
                cursor.execute('DELETE FROM fish_inventory WHERE id = ?', (fid,))
                
                # Calculate Scrap (Random 1-3)
                scrap = random.randint(1, 3)
                total_scrap += scrap
                deleted_count += 1
        
        self.cog.conn.commit()
        self.cog.add_material(self.original_interaction.user.id, "Scrap Metal", total_scrap)
        
        await interaction.response.send_message(f"✅ Berhasil men-salvage **{deleted_count}** ikan menjadi **{total_scrap}x Scrap Metal** 🔩!", ephemeral=True)
        
        # Refresh data
        cursor.execute('SELECT id, fish_name, rarity, weight, price FROM fish_inventory WHERE user_id = ? ORDER BY id DESC', (self.original_interaction.user.id,))
        self.all_rows = cursor.fetchall()
        self.max_pages = (len(self.all_rows) - 1) // self.items_per_page + 1
        if self.page >= self.max_pages: self.page = max(0, self.max_pages - 1)
        
        self.update_components()
        # Edit original message to reflect changes
        try:
            await self.original_interaction.edit_original_response(embed=self.build_embed(), view=self)
        except:
            pass

class FishingForgeView(discord.ui.View):
    def __init__(self, cog, interaction, owned_rods):
        super().__init__(timeout=120)
        self.cog = cog
        self.original_interaction = interaction
        self.owned_rods = owned_rods
        self.selected_rod = None
        
        self.update_components()

    def update_components(self):
        self.clear_items()
        
        # Select Rod
        options = []
        for rod in self.owned_rods:
            level = self.cog.get_rod_level(self.original_interaction.user.id, rod)
            options.append(discord.SelectOption(
                label=f"{rod} (+{level})",
                value=rod,
                emoji="🎣"
            ))
            
        select = discord.ui.Select(
            placeholder="Pilih pancingan untuk ditempa...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.select_rod_callback
        self.add_item(select)
        
        # Forge Button (Only if rod selected)
        if self.selected_rod:
            btn = discord.ui.Button(label="🔨 Tempa (Forge)", style=discord.ButtonStyle.danger)
            btn.callback = self.forge_callback
            self.add_item(btn)

    async def send_initial_message(self):
        user_scrap = self.cog.get_material(self.original_interaction.user.id, "Scrap Metal")
        user_pearl = self.cog.get_material(self.original_interaction.user.id, "Magic Pearl")
        
        embed = discord.Embed(title="⚒️ Forge (Tempa Pancingan)", description="Pilih pancingan di bawah untuk melihat biaya upgrade.", color=discord.Color.dark_red())
        embed.add_field(name="Material Kamu", value=f"🔩 Scrap Metal: **{user_scrap}**\n🔮 Magic Pearl: **{user_pearl}**", inline=False)
        await self.original_interaction.response.send_message(embed=embed, view=self)

    async def select_rod_callback(self, interaction: discord.Interaction):
        self.selected_rod = interaction.data["values"][0]
        self.update_components()
        
        # Calculate Cost
        level = self.cog.get_rod_level(interaction.user.id, self.selected_rod)
        next_level = level + 1
        
        # Cost Formula
        cost_scrap = next_level * 5 + 5
        cost_pearl = 0
        if next_level >= 5:
            cost_pearl = (next_level - 4) * 1
            
        embed = discord.Embed(title=f"⚒️ Forge: {self.selected_rod} (+{level} ➡️ +{next_level})", color=discord.Color.dark_red())
        embed.add_field(name="Biaya", value=f"🔩 Scrap Metal: **{cost_scrap}**\n🔮 Magic Pearl: **{cost_pearl}**", inline=False)
        
        # Check User Materials
        user_scrap = self.cog.get_material(interaction.user.id, "Scrap Metal")
        user_pearl = self.cog.get_material(interaction.user.id, "Magic Pearl")
        
        embed.add_field(name="Material Kamu", value=f"🔩 {user_scrap}\n🔮 {user_pearl}", inline=False)
        
        if user_scrap >= cost_scrap and user_pearl >= cost_pearl:
            embed.set_footer(text="Material cukup! Klik tombol Tempa.")
        else:
            embed.set_footer(text="Material tidak cukup!")
            
        await interaction.response.edit_message(embed=embed, view=self)

    async def forge_callback(self, interaction: discord.Interaction):
        if not self.selected_rod: return
        
        level = self.cog.get_rod_level(interaction.user.id, self.selected_rod)
        next_level = level + 1
        
        cost_scrap = next_level * 5 + 5
        cost_pearl = 0
        if next_level >= 5:
            cost_pearl = (next_level - 4) * 1
            
        user_scrap = self.cog.get_material(interaction.user.id, "Scrap Metal")
        user_pearl = self.cog.get_material(interaction.user.id, "Magic Pearl")
        
        if user_scrap < cost_scrap or user_pearl < cost_pearl:
            await interaction.response.send_message("❌ Material tidak cukup!", ephemeral=True)
            return
            
        # Deduct Materials
        self.cog.add_material(interaction.user.id, "Scrap Metal", -cost_scrap)
        self.cog.add_material(interaction.user.id, "Magic Pearl", -cost_pearl)
        
        # Upgrade Rod
        self.cog.update_rod_level(interaction.user.id, self.selected_rod, next_level)
        
        await interaction.response.send_message(f"🎉 **SUKSES!** {self.selected_rod} berhasil ditempa ke level **+{next_level}**!", ephemeral=True)
        
        # Refresh
        await self.select_rod_callback(interaction)


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
