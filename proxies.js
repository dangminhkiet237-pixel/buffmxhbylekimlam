// api/proxies.js
export default async function handler(req, res) {
    const { protocol = 'http', count = 10, url } = req.query;
    const DEFAULT_APIS = {
        http: 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        socks4: 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt',
        socks5: 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt'
    };
    const apiUrl = url || DEFAULT_APIS[protocol];
    if (!apiUrl) {
        return res.status(400).json({ error: 'Invalid protocol' });
    }
    try {
        const response = await fetch(apiUrl);
        const text = await response.text();
        let proxies = text.split('\n').filter(line => line.trim() !== '');
        // Lấy ngẫu nhiên
        const shuffled = proxies.sort(() => 0.5 - Math.random());
        const selected = shuffled.slice(0, parseInt(count) || 10);
        res.json({ proxies: selected });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
}
