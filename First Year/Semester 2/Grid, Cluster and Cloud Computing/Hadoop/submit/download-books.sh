#!/usr/bin/env bash
set -eux

books=(
  "98:A_Tale_of_Two_Cities:https://www.gutenberg.org/files/98/98-0.txt"
  "1342:Pride_and_Prejudice:https://www.gutenberg.org/files/1342/1342-0.txt"
  "1400:Great_Expectations:https://www.gutenberg.org/files/1400/1400-0.txt"
  "158:Emma:https://www.gutenberg.org/files/158/158-0.txt"
  "161:Sense_and_Sensibility:https://www.gutenberg.org/files/161/161-0.txt"
  "2701:Moby_Dick:https://www.gutenberg.org/files/2701/2701-0.txt"
  "345:Dracula:https://www.gutenberg.org/files/345/345-0.txt"
  "4300:Ulysses:https://www.gutenberg.org/files/4300/4300-0.txt"
  "1023:Bleak_House:https://www.gutenberg.org/files/1023/1023-0.txt"
  "766:David_Copperfield:https://www.gutenberg.org/files/766/766-0.txt"
)

index=1

for entry in "${books[@]}"; do
  IFS=":" read -r id name url <<< "$entry"
  printf "Downloading eBook #%s (%s) → saving as book%s.txt\n" "$id" "$name" "$index"
  curl --http1.1 --retry 5 --retry-delay 2 -fSL "$url" -o "book${index}.txt"

  filesize_bytes=$(wc -c < "book${index}.txt")
  filesize_kb=$((filesize_bytes / 1024))
  printf "Size of book%s.txt: %d KB\n\n" "$index" "$filesize_kb"

  ((index++))
done

echo "All books have been downloaded."