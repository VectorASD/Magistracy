[Console]::OutputEncoding = [System.Text.Encoding]::UTF8 # противокракозябровое оружие, но нужен Write-Host
chcp 65001 # так и не вышло удалить кракозябры ;'-}

# $ip = "192.168.49.2"   # IP Minikube или кластера
# $ip = (minikube ip).Trim()
$ip = "::1" # при использовании   kubectl port-forward svc/nginx -n rgz 80:80
$hostEntry = "$ip rgz.local"
$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"

if (-not (Select-String -Path $hostsPath -Pattern "rgz.local" -Quiet)) {
    Add-Content -Path $hostsPath -Value $hostEntry
    Write-Host "Запись добавлена: $hostEntry" # Write-Output пишет кракозябры
} else {
    Write-Host "Запись уже существует"
}

Write-Host "Нажмите Enter для выхода..."
Read-Host
