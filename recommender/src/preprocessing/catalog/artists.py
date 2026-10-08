"""
Curated seed artists used to build the MusicMatch song catalog.

The catalog pipeline uses these names to:
1. Find the matching artist in MusicBrainz.
2. Retrieve popular recordings from ListenBrainz.
3. Build a broad catalog across decades and genres.

The list is intentionally diverse so MusicMatch can recommend music
from multiple eras and styles rather than overfitting to one genre.
"""

SEED_ARTISTS = [
    # --------------------------------------------------
    # 1970s / Classic Rock / Pop
    # --------------------------------------------------
    "Fleetwood Mac",
    "Pink Floyd",
    "Queen",
    "David Bowie",
    "Led Zeppelin",
    "Elton John",
    "Stevie Wonder",
    "Billy Joel",
    "Eagles",
    "ABBA",

    # --------------------------------------------------
    # 1980s
    # --------------------------------------------------
    "Michael Jackson",
    "Prince",
    "Madonna",
    "Metallica",
    "The Cure",
    "Depeche Mode",
    "Bon Jovi",
    "Whitney Houston",
    "George Michael",
    "Tears for Fears",

    # --------------------------------------------------
    # 1990s
    # --------------------------------------------------
    "Nirvana",
    "Radiohead",
    "Nas",
    "2Pac",
    "The Notorious B.I.G.",
    "Mariah Carey",
    "Green Day",
    "Foo Fighters",
    "Pearl Jam",
    "Outkast",

    # --------------------------------------------------
    # 2000s
    # --------------------------------------------------
    "Eminem",
    "Beyoncé",
    "The Strokes",
    "Daft Punk",
    "Linkin Park",
    "Coldplay",
    "Kanye West",
    "Alicia Keys",
    "The Killers",
    "Rihanna",

    # --------------------------------------------------
    # 2010s
    # --------------------------------------------------
    "Kendrick Lamar",
    "Frank Ocean",
    "Arctic Monkeys",
    "The Weeknd",
    "Drake",
    "Adele",
    "Bruno Mars",
    "Lana Del Rey",
    "Tame Impala",
    "SZA",

    # --------------------------------------------------
    # 2020s
    # --------------------------------------------------
    "Billie Eilish",
    "Dua Lipa",
    "Olivia Rodrigo",
    "Doja Cat",
    "Sabrina Carpenter",
    "Chappell Roan",
    "Tyler, The Creator",
    "Bad Bunny",
    "Harry Styles",
    "Tate McRae",

    # --------------------------------------------------
    # Country / Folk
    # --------------------------------------------------
    "Johnny Cash",
    "Dolly Parton",
    "Willie Nelson",
    "Shania Twain",
    "Chris Stapleton",

    # --------------------------------------------------
    # Jazz / Soul / R&B
    # --------------------------------------------------
    "Miles Davis",
    "Aretha Franklin",
    "Marvin Gaye",
    "Lauryn Hill",
    "Usher",

    # --------------------------------------------------
    # Latin
    # --------------------------------------------------
    "Shakira",
    "Daddy Yankee",
    "Juanes",
    "J Balvin",
    "Karol G",

    # --------------------------------------------------
    # Reggae
    # --------------------------------------------------
    "Bob Marley & The Wailers",
    "Jimmy Cliff",
    "Sean Paul",
    "Shaggy",
    "Damian Marley",

    # --------------------------------------------------
    # More 1990s Rock / Alternative
    # --------------------------------------------------
    "Oasis",
    "The Smashing Pumpkins",
    "Red Hot Chili Peppers",
    "Alice in Chains",
    "Soundgarden",
    "Stone Temple Pilots",
    "The Cranberries",
    "Weezer",

    # --------------------------------------------------
    # More 1990s Hip-Hop
    # --------------------------------------------------
    "Wu-Tang Clan",
    "Jay-Z",
    "Snoop Dogg",
    "A Tribe Called Quest",
    "Mobb Deep",
    "Missy Elliott",
    "Dr. Dre",

    # --------------------------------------------------
    # More R&B
    # --------------------------------------------------
    "Janet Jackson",
    "Mary J. Blige",
    "TLC",
    "Aaliyah",
    "Boyz II Men",
    "Erykah Badu",
    "D'Angelo",

    # --------------------------------------------------
    # More 2020s
    # --------------------------------------------------
    "Taylor Swift",
    "Charli XCX",
    "Gracie Abrams",
    "Morgan Wallen",
    "Zach Bryan",
    "Rauw Alejandro",
    "Feid",
    "Peso Pluma",

    # --------------------------------------------------
    # More Country
    # --------------------------------------------------
    "George Strait",
    "Garth Brooks",
    "Reba McEntire",
    "Alan Jackson",
    "Tim McGraw",
    "Faith Hill",
    "Kacey Musgraves",
    "Luke Combs",

    # --------------------------------------------------
    # More Latin
    # --------------------------------------------------
    "Selena",
    "Luis Miguel",
    "Marc Anthony",
    "Juan Luis Guerra",
    "Romeo Santos",
    "Rosalía",

    # --------------------------------------------------
    # More Jazz
    # --------------------------------------------------
    "John Coltrane",
    "Thelonious Monk",
    "Dave Brubeck",
    "Ella Fitzgerald",
    "Billie Holiday",
    "Herbie Hancock",
]