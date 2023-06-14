import hashlib 

def hashing(path):
    md5_hash = hashlib.md5()
    with open(path,"rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            md5_hash.update(byte_block)
        final=md5_hash.hexdigest()
    return(final)

