<?php
// update_xu.php
header('Content-Type: application/json');

$key = $_POST['key'] ?? '';
$xu_nhan = intval($_POST['xu_nhan'] ?? 0);

if (empty($key) || $xu_nhan <= 0) {
    echo json_encode(['error' => 'Invalid data']);
    exit;
}

// Đọc file key hiện tại
$file = 'keyttcfb.txt';
$lines = file($file, FILE_IGNORE_NEW_LINES);
$new_lines = [];

$found = false;
foreach ($lines as $line) {
    $parts = explode('|', $line);
    if (count($parts) >= 3 && $parts[0] == $key) {
        // Lấy số xu hiện tại
        $xu_part = $parts[2];
        if (strpos($xu_part, 'xu') === 0) {
            $xu_current = intval(substr($xu_part, 2));
        } else {
            $xu_current = intval($xu_part);
        }
        
        // Trừ xu
        $xu_new = max(0, $xu_current - $xu_nhan);
        $parts[2] = 'xu' . $xu_new;
        $new_lines[] = implode('|', $parts);
        $found = true;
    } else {
        $new_lines[] = $line;
    }
}

if ($found) {
    file_put_contents($file, implode("\n", $new_lines));
    echo json_encode(['xu_con_lai' => $xu_new]);
} else {
    echo json_encode(['error' => 'Key not found']);
}
?>
