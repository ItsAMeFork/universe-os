// Serves the cloud-init seed for the first boot of the build VM (QEMU user network reaches the host as 10.0.2.2).
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {join,basename} from 'node:path';
const dir=process.argv[2],port=Number(process.argv[3]||8123);
createServer(async(req,res)=>{
 const name=basename(new URL(req.url,'http://x').pathname);
 try{const body=await readFile(join(dir,name));res.writeHead(200);res.end(body);}catch{res.writeHead(404);res.end();}
}).listen(port,'127.0.0.1',()=>console.log(`seed op poort ${port}`));
