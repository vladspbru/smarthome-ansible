#/bin/sh

#rm *.retry
#rm *.log

#ansible bbb -u debian -k  -m ping
#ansible bbb -u debian -k -a "ip addr"
#1 ansible-playbook -u debian -k users.yml --extra-vars "ansible_become_pass=temppwd"

#1 
ansible-playbook playbook.yml $1
#-vvv
#--syntax-check


#2 ansible-playbook update.yml
