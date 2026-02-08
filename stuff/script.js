// elem_tweets = document.querySelector('[data-testid="cellInnerDiv"]')
// elem_tweets[0].innerText
// document.querySelectorAll('[aria-labelledby="accessible-list-8"] [data-testid="cellInnerDiv"]').forEach(e=>extract_data_from_tweet(e.innerText))
// document.querySelectorAll('[data-testid="tweet"]')
// get id: tweet_elem.querySelectorAll('a')[3]

function is_number(str)
{
    // numbers with digits and negative
    if (/^-?\d+(\.\d+)?$/.test(str)) {
        return true;
    }   

    // stuff like 55.2K
    if (/^-?\d+(\.\d+)?[KMBTkmt]$/.test(str)) {
        return true;
    }
    return false;
}

function remove_quote(text){
    let lines = text
    if (!Array.isArray(lines)){
        lines = lines.split("\n");
    }
    for (let i = 0; i < lines.length; i++){
        if (lines[i] == "Quote"){
            return lines.slice(0, i);
        }
    }
    return lines
}

function extract_data_from_tweet(id, text){
    if (!text){
        return null;
    }
    lines=text.split("\n");
    username = lines[1]
    if (username[0] != "@"){
        // console.log("Invalid username", username);
        return null;
    }
    tweet_dt = lines[3]
    const date_regex = /[A-Za-z]+ \d{1,2}, \d{4}/g;
    if (!date_regex.test(tweet_dt)){
        // console.log("Invalid date", tweet_dt);
        return null;
    }
    //lines = lines.slice(0, -3); //Remove num replies, reposts and likes

    for (let i = lines.length - 1; i >= 0; i--) {
        if (is_number(lines[i])){
            lines.pop();
        }
    }

    lines = lines.slice(4); //Remove name, username, . and date
    lines = remove_quote(lines)

    if (lines[lines.length-1]=="Show more"){
        return null;
    }

    tweet = lines.join("\n");

    // console.log(`Id: ${id} username: ${username}, date: ${tweet_dt}: ${tweet}`)
    // console.log(`Id: ${id} username: ${username}, date: ${tweet_dt}`)
    return new Tweet(id, username, tweet, tweet_dt, text);
} 

class Tweet{
    constructor(id, username, text, date, original_text="") {
        this.id = id;
        this.username = username
        this.text = text;
        this.date = date;
        this.original_text=original_text
    }
}

class Scraper {
    constructor() {
        this.interval_id = null;
        this.is_active = false;
        this.tweet_map={};
    }

    start(interval = 1000) {
        this.stop();
        
        this.interval_id = setInterval(() => {
            this.scrape_tweets()
        }, interval);
        
        this.is_active = true;
        console.log("Scraping started with interval:", interval, "ms");
    }

    stop() {
        if (this.interval_id) {
            clearInterval(this.interval_id);
            this.interval_id = null;
            this.is_active = false;
            console.log("Scraping stopped");
        }
    }

    scrape_tweets(){
        const elem_tweets = document.querySelectorAll('[data-testid="tweet"]')
        // console.log(`Got ${elem_tweets.length}`)
        elem_tweets.forEach(elem_tweet=>{
            const url = elem_tweet.querySelectorAll('a')[3].getAttribute('href');
            const id = url.split('/').pop();
            const raw_text = elem_tweet.innerText;
            const tweet = extract_data_from_tweet(id, raw_text)
            if (tweet != null && ! (tweet.id in this.tweet_map)){
                this.tweet_map[tweet.id]=tweet;
                // console.log(`Added new tweet ${id}`)
                //console.log(`Added new tweet: Id: ${id} username: ${tweet.username}, date: ${tweet.date}\n${tweet.original_text}\n\n${tweet.text}\n\n`)
                console.log(`Added new tweet: Id: ${id} username: ${tweet.username}, date: ${tweet.date}\n\n${tweet.text}\n\n`)
                // console.log(this.print_scraped_tweets())
            }
        })
    }

    print_scraped_tweets(){
        for (let id in this.tweet_map) {
            const tweet = this.tweet_map[id];
            console.log(`Id: ${id} username: ${tweet.username}, date: ${tweet.date}\n${tweet.text}\n\n`)
        }
    }
}

scraper = new Scraper()
scraper.start()

//let tweet_text="AZEALIA BANKS\n@AZEALIASPEAKS\n·\nJul 31, 2018\nMiss Camaraderie (Bon Vivant Remix) - Available now on iTunes, Apple Music, and more! \nhttp://\nhyperurl.co/MCREMIX\n50\n22\n107"
let tweet_text="AZEALIA BANKS\n@AZEALIASPEAKS\n·\nJul 9, 2018\nTREASURE ISLAND | \nhttps://\nyoutube.com/watch?v=HFnVIE\nlNup4\n… | \nhttp://\nsmarturl.it/AB_treasureisl\nand\n…\nyoutube.com\nAzealia Banks - Treasure Island (Official Audio)\nExclusively Licensed by Entertainment One. Fantasea II Coming Soon.Stream: http://smarturl.it/AB_treasureisland\n21\n18\n73"


document.onload = function() {};