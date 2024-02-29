import hashlib
id = "vdyjc1dnhfs3z4f2t"


username = "prisonline1"
pan = "9860260101211209"
salt = "N^OJD.;ydzn+@$aTx"
amount = 1000
clientId = id

sms = "258654"
transid = "5dcd7021-8a2c-4168-ad93-a990716b648e"

second = f"vdyjc1dnhfs3z4f2tN^OJD.;ydzn+@$aTx{sms}{transid}"
data_to_hash = f"{username}{pan}{salt}{amount}{clientId}"
print(second)
hash_key = hashlib.new('SHA3-256', second.encode()).hexdigest()

print(f"Hash Key: {hash_key}")
