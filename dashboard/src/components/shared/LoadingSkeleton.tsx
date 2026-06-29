import Skeleton from '@mui/material/Skeleton';
import Box from '@mui/material/Box';

interface LoadingSkeletonProps {
  count?: number;
  variant?: 'text' | 'rectangular' | 'circular';
  height?: number;
}

export function LoadingSkeleton({
  count = 3,
  variant = 'rectangular',
  height = 40,
}: LoadingSkeletonProps): JSX.Element {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {Array.from({ length: count }, (_, index: number) => (
        <Skeleton
          key={index}
          variant={variant}
          height={height}
          animation="wave"
        />
      ))}
    </Box>
  );
}
